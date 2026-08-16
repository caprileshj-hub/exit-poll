import asyncio
import threading

from backend import app as app_backend


def test_seed_historicos_startup_no_bloquea(monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def slow_seed():
        started.set()
        release.wait(timeout=5)

    monkeypatch.setattr(app_backend, "_seed_historicos", slow_seed)
    app_backend.app.state.historicos_seed_task = None

    async def exercise():
        await app_backend.seed_historicos_startup()
        task = app_backend.app.state.historicos_seed_task
        assert task is not None
        try:
            for _ in range(100):
                if started.is_set():
                    break
                await asyncio.sleep(0.01)
            assert started.is_set()
            assert not task.done()
        finally:
            release.set()
            await task

    asyncio.run(exercise())
