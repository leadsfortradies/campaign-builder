"""Phone notifications through ntfy. Best-effort: never raises."""

import threading
import urllib.request

from . import config


def notify(title, message, link_path=""):
    if not config.NTFY_TOPIC:
        return

    def _send():
        try:
            req = urllib.request.Request(
                f"{config.NTFY_SERVER}/{config.NTFY_TOPIC}",
                data=message.encode("utf-8"),
                method="POST",
            )
            req.add_header("Title", title.encode("ascii", "ignore").decode() or "Campaign Builder")
            if config.PUBLIC_URL and link_path:
                req.add_header("Click", config.PUBLIC_URL + link_path)
            urllib.request.urlopen(req, timeout=10).read()
        except Exception as exc:  # noqa: BLE001 - notifications must never break a job
            print(f"[notify] failed: {exc}")

    threading.Thread(target=_send, daemon=True).start()
