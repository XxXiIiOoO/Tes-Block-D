from __future__ import annotations

from dataclasses import dataclass

from app.models.run import Run, RunLog, RunStatus


ERROR_KEYWORDS = (
    "error",
    "exception",
    "traceback",
    "failed",
    "revert",
    "panic",
)
WARNING_KEYWORDS = ("warning", "warn", "deprecated")
NETWORK_KEYWORDS = (
    "network is unreachable",
    "temporary failure in name resolution",
    "name or service not known",
    "connection refused",
    "connection reset",
    "timed out",
)


@dataclass(frozen=True)
class ParsedLog:
    source: str
    severity: str
    content: str


@dataclass(frozen=True)
class RunMetrics:
    duration_seconds: float | None
    queue_time_seconds: float | None
    total_logs: int
    stdout_lines: int
    stderr_lines: int
    system_lines: int
    info_count: int
    warning_count: int
    error_count: int


@dataclass(frozen=True)
class RunSignal:
    severity: str
    title: str
    detail: str


@dataclass(frozen=True)
class RunAnalysis:
    summary: str
    failure_category: str | None
    latest_error: str | None
    metrics: RunMetrics
    signals: list[RunSignal]
    recommendations: list[str]


#Zdes sobrana logika compute_duration_seconds, tak ee proshche podderzhivat.
def compute_duration_seconds(run: Run) -> float | None:
    if run.started_at is None or run.finished_at is None:
        return None
    return round((run.finished_at - run.started_at).total_seconds(), 2)


#Zdes sobrana logika compute_queue_time_seconds, tak ee proshche podderzhivat.
def compute_queue_time_seconds(run: Run) -> float | None:
    if run.started_at is None:
        return None
    return round((run.started_at - run.created_at).total_seconds(), 2)


#Eto otdelnyy shag parse_log_message, chtoby ne kopipastit odno i to zhe.
def parse_log_message(message: str) -> ParsedLog:
    source = "system"
    content = message
    if message.startswith("[stdout] "):
        source = "stdout"
        content = message[len("[stdout] ") :]
    elif message.startswith("[stderr] "):
        source = "stderr"
        content = message[len("[stderr] ") :]

    lowered = content.lower()
    severity = "info"
    if source == "stderr" or any(keyword in lowered for keyword in ERROR_KEYWORDS):
        severity = "error"
    elif any(keyword in lowered for keyword in WARNING_KEYWORDS):
        severity = "warning"

    return ParsedLog(source=source, severity=severity, content=content)


#Eto otdelnyy shag collect_run_metrics, chtoby ne kopipastit odno i to zhe.
def collect_run_metrics(run: Run) -> RunMetrics:
    stdout_lines = 0
    stderr_lines = 0
    system_lines = 0
    info_count = 0
    warning_count = 0
    error_count = 0

    for log in run.logs:
        parsed = parse_log_message(log.message)
        if parsed.source == "stdout":
            stdout_lines += 1
        elif parsed.source == "stderr":
            stderr_lines += 1
        else:
            system_lines += 1

        if parsed.severity == "error":
            error_count += 1
        elif parsed.severity == "warning":
            warning_count += 1
        else:
            info_count += 1

    return RunMetrics(
        duration_seconds=compute_duration_seconds(run),
        queue_time_seconds=compute_queue_time_seconds(run),
        total_logs=len(run.logs),
        stdout_lines=stdout_lines,
        stderr_lines=stderr_lines,
        system_lines=system_lines,
        info_count=info_count,
        warning_count=warning_count,
        error_count=error_count,
    )


#Funkciya detect_failure_category zakryvaet konkretnuyu zadachu v etom meste.
def detect_failure_category(run: Run, parsed_logs: list[ParsedLog]) -> str | None:
    combined_text = "\n".join(
        [run.result_summary or "", *[parsed.content for parsed in parsed_logs]]
    ).lower()

    if run.exit_code == 124 or "timed out" in combined_text or "timeout" in combined_text:
        return "timeout"
    if "docker execution error" in combined_text or "docker error:" in combined_text:
        return "docker"
    if any(keyword in combined_text for keyword in NETWORK_KEYWORDS):
        return "network"
    if "no module named" in combined_text or "command not found" in combined_text:
        return "dependency"
    if "revert" in combined_text or "panic code" in combined_text or "invalid opcode" in combined_text:
        return "contract"
    if "assertionerror" in combined_text or "assertion failed" in combined_text:
        return "assertion"
    if "traceback" in combined_text or "exception" in combined_text:
        return "exception"
    if run.status == RunStatus.cancelled:
        return "cancelled"
    if run.status == RunStatus.failed:
        return "generic_failure"
    return None


#Zdes sobrana logika _build_signals, tak ee proshche podderzhivat.
def _build_signals(run: Run, metrics: RunMetrics, parsed_logs: list[ParsedLog]) -> list[RunSignal]:
    signals: list[RunSignal] = []
    failure_category = detect_failure_category(run, parsed_logs)

    if run.status == RunStatus.queued:
        signals.append(
            RunSignal(
                severity="info",
                title="Запуск в очереди",
                detail="Воркер ещё не начал выполнение этого запуска.",
            )
        )
    if run.status == RunStatus.running:
        signals.append(
            RunSignal(
                severity="info",
                title="Выполнение в процессе",
                detail=f"Запуск сейчас активен и уже сформировал {metrics.total_logs} строк логов.",
            )
        )

    category_signal_map: dict[str, tuple[str, str, str]] = {
        "timeout": (
            "error",
            "Тайм-аут выполнения",
            "Контейнер превысил заданный лимит времени и был остановлен воркером.",
        ),
        "docker": (
            "error",
            "Проблема рантайма Docker",
            "Воркер не смог корректно завершить жизненный цикл контейнера.",
        ),
        "network": (
            "warning",
            "Проблема сетевого доступа",
            "Во время запуска была попытка сетевой операции, которая завершилась ошибкой или была заблокирована.",
        ),
        "dependency": (
            "error",
            "Отсутствует зависимость или инструмент",
            "В образе контейнера не хватает Python-модуля или команды, необходимых для теста.",
        ),
        "contract": (
            "error",
            "Revert смарт-контракта или panic EVM",
            "Логи указывают на revert, panic-код или invalid opcode во время выполнения.",
        ),
        "assertion": (
            "warning",
            "Провал проверки assert",
            "Логика теста зафиксировала ошибку assertion.",
        ),
        "exception": (
            "error",
            "Необработанное исключение",
            "В логах обнаружен traceback или вывод исключения.",
        ),
        "generic_failure": (
            "warning",
            "Запуск завершился ошибкой",
            "Контейнер завершился неуспешно, но без более точного паттерна причины.",
        ),
        "cancelled": (
            "info",
            "Запуск отменён",
            "Пользователь запросил отмену запуска, поэтому результат не учитывается как успешный.",
        ),
    }
    if failure_category in category_signal_map:
        severity, title, detail = category_signal_map[failure_category]
        signals.append(RunSignal(severity=severity, title=title, detail=detail))

    if metrics.stderr_lines and run.status == RunStatus.finished:
        signals.append(
            RunSignal(
                severity="warning",
                title="Успешный запуск с выводом stderr",
                detail="Запуск завершился успешно, но stderr содержит диагностический шум, который стоит проверить.",
            )
        )
    if metrics.queue_time_seconds is not None and metrics.queue_time_seconds > 10:
        signals.append(
            RunSignal(
                severity="warning",
                title="Обнаружено ожидание в очереди",
                detail=f"Запуск ждал {metrics.queue_time_seconds:.2f}с перед стартом воркера.",
            )
        )
    if metrics.duration_seconds is not None and metrics.duration_seconds > 20:
        signals.append(
            RunSignal(
                severity="info",
                title="Длительное выполнение",
                detail=f"Запуск занял {metrics.duration_seconds:.2f}с от старта до завершения.",
            )
        )
    if run.status == RunStatus.failed and metrics.total_logs == 0:
        signals.append(
            RunSignal(
                severity="warning",
                title="Нет диагностического вывода",
                detail="Запуск завершился ошибкой без логов, поэтому может понадобиться отладка на уровне образа.",
            )
        )

    deduplicated: list[RunSignal] = []
    seen = set()
    for signal in signals:
        key = (signal.severity, signal.title)
        if key in seen:
            continue
        deduplicated.append(signal)
        seen.add(key)
    return deduplicated


#Zdes sobrana logika _build_recommendations, tak ee proshche podderzhivat.
def _build_recommendations(
    run: Run,
    metrics: RunMetrics,
    failure_category: str | None,
) -> list[str]:
    recommendations: list[str] = []

    if failure_category == "timeout":
        recommendations.append(
            "Уменьшите нагрузку или увеличьте DOCKER_RUN_TIMEOUT_SECONDS для более долгих блокчейн-сценариев."
        )
    if failure_category == "network":
        recommendations.append(
            "Если тесту нужен RPC или доступ к пакетам, проверьте DOCKER_NETWORK_DISABLED и по возможности уберите внешние зависимости."
        )
    if failure_category == "dependency":
        recommendations.append(
            "Добавьте отсутствующий CLI-инструмент или Python-пакет в Docker-образ этого теста."
        )
    if failure_category == "contract":
        recommendations.append(
            "Проверьте calldata, allowances, balances и ожидаемые условия revert в проблемном контрактном потоке."
        )
    if failure_category == "assertion":
        recommendations.append(
            "Сравните ожидаемые и фактические значения в логах, чтобы понять, какое бизнес-правило нарушено."
        )
    if failure_category == "exception":
        recommendations.append(
            "Изучите traceback с первой строки ошибки и добавьте структурированные контрольные точки вокруг проблемной операции."
        )
    if failure_category == "cancelled":
        recommendations.append(
            "Проверьте частичные логи и при необходимости перезапустите тест после корректировки сценария или лимитов выполнения."
        )
    if run.status == RunStatus.finished and metrics.stderr_lines:
        recommendations.append(
            "Очистите шум в stderr или оформите предупреждения как структурированную диагностику, чтобы успешные запуски было проще анализировать."
        )
    if metrics.queue_time_seconds is not None and metrics.queue_time_seconds > 10:
        recommendations.append(
            "Ожидание в очереди повышено: рассмотрите увеличение числа воркеров или снижение фоновой нагрузки."
        )
    if not recommendations:
        recommendations.append(
            "Запуск выглядит стабильным. Продолжайте выгружать результаты и сравнивать длительность, чтобы вовремя замечать регрессии."
        )

    return recommendations


#Zdes sobrana logika build_run_summary, tak ee proshche podderzhivat.
def build_run_summary(
    run: Run,
    metrics: RunMetrics,
    failure_category: str | None,
) -> str:
    if run.status == RunStatus.queued:
        return "Запуск поставлен в очередь и ожидает воркер для старта изолированного контейнера."
    if run.status == RunStatus.running:
        return f"Запуск всё ещё выполняется. Уже сохранено {metrics.total_logs} строк логов."
    if run.status == RunStatus.cancelled:
        return "Запуск отменён пользователем. Сохранённые логи доступны для проверки частичного выполнения."

    duration_text = (
        f"{metrics.duration_seconds:.2f}s"
        if metrics.duration_seconds is not None
        else "неизвестное время"
    )
    if run.status == RunStatus.finished:
        return (
            f"Запуск завершился успешно за {duration_text}. "
            f"Собрано {metrics.stdout_lines} строк stdout и {metrics.stderr_lines} строк stderr."
        )

    category_text = failure_category.replace("_", " ") if failure_category else "неизвестная проблема"
    return (
        f"Запуск завершился ошибкой через {duration_text}. Категория: {category_text}. "
        f"Проверьте сигналы и фрагменты логов ниже для поиска вероятной первопричины."
    )


#Eto otdelnyy shag analyze_run, chtoby ne kopipastit odno i to zhe.
def analyze_run(run: Run) -> RunAnalysis:
    parsed_logs = [parse_log_message(log.message) for log in run.logs]
    metrics = collect_run_metrics(run)
    failure_category = detect_failure_category(run, parsed_logs)
    signals = _build_signals(run, metrics, parsed_logs)
    latest_error = next(
        (parsed.content for parsed in reversed(parsed_logs) if parsed.severity == "error"),
        None,
    )
    recommendations = _build_recommendations(run, metrics, failure_category)
    summary = build_run_summary(run, metrics, failure_category)

    return RunAnalysis(
        summary=summary,
        failure_category=failure_category,
        latest_error=latest_error,
        metrics=metrics,
        signals=signals,
        recommendations=recommendations,
    )


#Funkciya serialize_run_log_metadata zakryvaet konkretnuyu zadachu v etom meste.
def serialize_run_log_metadata(log: RunLog) -> ParsedLog:
    return parse_log_message(log.message)
