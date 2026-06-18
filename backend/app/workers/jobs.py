from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.project import Project
from app.models.run import Run, RunLog, RunStatus
from app.models.test import Test
from app.services.docker_runner import AsyncDockerRunner, DockerRunnerError
from app.workers.broker import broker


#Tut ya vynes append_log, chtoby ne razduvat ostalnoy kod.
def append_log(run: Run, message: str) -> None:
    run.logs.append(RunLog(message=message))


#Tut obrabatyvayu persist_output, vse po delu i bez lishnego.
def persist_output(run: Run, stdout: str, stderr: str) -> None:
    if stdout:
        for line in stdout.splitlines():
            append_log(run, f"[stdout] {line}")
    if stderr:
        for line in stderr.splitlines():
            append_log(run, f"[stderr] {line}")
    if not stdout and not stderr:
        append_log(run, "Контейнер не вернул вывод")


#Tut ya vynes run_test_job, chtoby ne razduvat ostalnoy kod.
@broker.task
async def run_test_job(run_id: int) -> None:
    db = SessionLocal()
    try:
        run = db.scalar(
            select(Run)
            .join(Test, Run.test_id == Test.id)
            .join(Project, Test.project_id == Project.id)
            .where(Run.id == run_id)
        )
        if run is None:
            return
        if run.status == RunStatus.cancelled:
            append_log(run, "Запуск отменён до старта воркера")
            db.add(run)
            db.commit()
            return

        test = db.scalar(select(Test).where(Test.id == run.test_id))
        if test is None:
            run.status = RunStatus.failed
            run.finished_at = datetime.now(timezone.utc)
            run.result_summary = "Конфигурация теста не найдена"
            db.add(run)
            db.commit()
            return

        run.status = RunStatus.running
        run.started_at = datetime.now(timezone.utc)
        append_log(run, "Подготовка изолированного Docker-окружения для теста")
        db.add(run)
        db.commit()

        runner = AsyncDockerRunner()
        result = await runner.execute_test(test, run_id=run.id)

        run = db.scalar(select(Run).where(Run.id == run_id))
        if run is None:
            return
        if run.status == RunStatus.cancelled:
            persist_output(run, result.stdout, result.stderr)
            run.exit_code = result.exit_code
            append_log(run, "Контейнер остановлен после запроса отмены; итоговый статус сохранён как отменённый")
            db.add(run)
            db.commit()
            return

        persist_output(run, result.stdout, result.stderr)
        run.exit_code = result.exit_code
        run.finished_at = datetime.now(timezone.utc)
        run.status = RunStatus.finished if result.exit_code == 0 else RunStatus.failed
        if result.timed_out:
            run.result_summary = "Превышен лимит времени выполнения"
            append_log(run, "Выполнение контейнера превысило тайм-аут и было остановлено")
        elif result.exit_code == 0:
            run.result_summary = "Тест завершился успешно"
        else:
            run.result_summary = "Тест завершился с ошибкой"

        db.add(run)
        db.commit()
    except DockerRunnerError as exc:
        run = db.scalar(select(Run).where(Run.id == run_id))
        if run is not None:
            run.status = RunStatus.failed
            run.finished_at = datetime.now(timezone.utc)
            run.exit_code = -1
            run.result_summary = "Ошибка выполнения Docker"
            append_log(run, f"Ошибка Docker: {exc}")
            db.add(run)
            db.commit()
    except Exception as exc:  # pragma: no cover - defensive guard for background jobs
        run = db.scalar(select(Run).where(Run.id == run_id))
        if run is not None:
            run.status = RunStatus.failed
            run.finished_at = datetime.now(timezone.utc)
            run.exit_code = -1
            run.result_summary = "Непредвиденная ошибка воркера"
            append_log(run, f"Ошибка воркера: {exc}")
            db.add(run)
            db.commit()
        raise
    finally:
        db.close()
