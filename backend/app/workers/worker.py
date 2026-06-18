import asyncio

from app.db.session import init_db
from app.workers.broker import broker
from app.workers.queue import wait_for_redis

# Import the jobs module so that @broker.task decorated functions are registered.
import app.workers.jobs  # noqa: F401


#Tut obrabatyvayu main, vse po delu i bez lishnego.
async def main() -> None:
    init_db()
    wait_for_redis()
    await broker.startup()
    try:
        from taskiq.api import run_receiver_event_loop
        await run_receiver_event_loop(broker)
    except KeyboardInterrupt:
        pass
    finally:
        await broker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
