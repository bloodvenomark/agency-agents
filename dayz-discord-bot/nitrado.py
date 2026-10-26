"""Schlanker Client für die Nitrado-API (Dateien lesen/schreiben, Status, Neustart)."""

import aiohttp

API = "https://api.nitrado.net"


class NitradoError(Exception):
    pass


class Nitrado:
    def __init__(self, token: str, service_id: str):
        self.service_id = service_id
        self._headers = {"Authorization": f"Bearer {token}"}
        self._session: aiohttp.ClientSession | None = None

    async def _http(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60)
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _api(self, method: str, path: str, **kwargs) -> dict:
        http = await self._http()
        url = f"{API}/services/{self.service_id}/gameservers{path}"
        async with http.request(method, url, headers=self._headers, **kwargs) as r:
            data = await r.json(content_type=None)
            if r.status >= 400 or data.get("status") == "error":
                raise NitradoError(f"{method} {path}: {r.status} {data.get('message')}")
            return data.get("data", {})

    async def gameserver(self) -> dict:
        """Details zum Gameserver (Status, Pfade, Benutzername ...)."""
        return (await self._api("GET", ""))["gameserver"]

    async def status(self) -> str:
        """z. B. 'started', 'stopped', 'restarting', 'starting'."""
        return (await self.gameserver()).get("status", "unknown")

    async def restart(self, message: str = "Shop-Lieferung"):
        await self._api("POST", "/restart", params={"message": message})

    async def list_dir(self, directory: str) -> list[dict]:
        data = await self._api("GET", "/file_server/list", params={"dir": directory})
        return data.get("entries", [])

    async def download(self, file_path: str) -> str:
        data = await self._api("GET", "/file_server/download", params={"file": file_path})
        url = data["token"]["url"]
        http = await self._http()
        async with http.get(url) as r:
            if r.status >= 400:
                raise NitradoError(f"Download {file_path}: {r.status}")
            raw = await r.read()
        return raw.decode("utf-8", errors="replace")

    async def upload(self, file_path: str, content: str):
        directory, _, name = file_path.rpartition("/")
        data = await self._api(
            "POST", "/file_server/upload", params={"path": directory, "file": name}
        )
        token = data["token"]
        http = await self._http()
        async with http.post(
            token["url"],
            data=content.encode("utf-8"),
            headers={"token": token["token"], "Content-Type": "application/octet-stream"},
        ) as r:
            if r.status >= 400:
                raise NitradoError(f"Upload {file_path}: {r.status} {await r.text()}")
