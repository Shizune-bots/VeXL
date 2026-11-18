"""
File Hosting Upload Module

Provides upload functionality to buzzheavier.com (primary), fileditch.com (fallback 1), and pixeldrain.com (fallback 2)
for files that exceed Telegram's 2GB upload limit.
"""

import os
import asyncio
import aiohttp
import logging
import base64
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

from bot.config import conf
from bot.utils.log_utils import logger
from bot.utils.os_utils import size_of
from bot.utils.bot_utils import hbs as get_readable_file_size

LOGS = logging.getLogger(__name__)


class FileHostError(Exception):
    """Base exception for file hosting errors."""
    pass


class BuzzheavierUploader:
    """Upload files to buzzheavier.com."""

    BASE_URL = "https://w.buzzheavier.com"
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds

    def __init__(self, token: Optional[str] = None):
        self.token = token  # Account ID for authenticated uploads
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            headers = {"User-Agent": "VeXL-Bot/1.0"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            # Increase timeout for large file uploads
            timeout = aiohttp.ClientTimeout(total=3600, connect=30)
            self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self.session

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        session = await self._get_session()
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                async with session.request(method, url, **kwargs) as resp:
                    # Buzzheavier returns plain text URL on success
                    text = await resp.text()
                    if resp.status in (200, 201):
                        return {"success": True, "url": text.strip()}
                    # Try to parse as JSON for error responses
                    try:
                        data = await resp.json()
                        return data
                    except Exception:
                        raise FileHostError(f"Upload failed with status {resp.status}: {text}")
            except aiohttp.ClientConnectorError as e:
                last_error = e
                LOGS.warning(f"Connection error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
            except aiohttp.ClientError as e:
                last_error = e
                LOGS.warning(f"HTTP error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
            except asyncio.TimeoutError as e:
                last_error = e
                LOGS.warning(f"Timeout (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
            except Exception as e:
                last_error = e
                LOGS.warning(f"Unexpected error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")

            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))

        raise FileHostError(f"Request failed after {self.MAX_RETRIES} attempts: {last_error}")

    async def upload(self, filepath: str, progress_callback=None) -> Dict[str, Any]:
        """
        Upload a file to buzzheavier.com.

        Args:
            filepath: Path to the file to upload
            progress_callback: Optional async callback(current, total) for progress updates

        Returns:
            Dict with keys: download_url, filename, file_size
        """
        session = await self._get_session()

        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)

        # Buzzheavier uses PUT with raw file body
        # For anonymous: PUT https://w.buzzheavier.com/{filename}
        # For authenticated: PUT https://w.buzzheavier.com/{parentId}/{filename}
        upload_url = f"{self.BASE_URL}/{filename}"

        # Prepare headers
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # Read file and upload
        file_handle = open(filepath, "rb")
        try:
            file_data = file_handle.read()

            async with session.put(upload_url, data=file_data, headers=headers) as resp:
                text = await resp.text()
                if resp.status in (200, 201):
                    # Try to parse as JSON first (new API format)
                    try:
                        import json
                        data = json.loads(text)
                        if data.get("code") == 201 and data.get("data", {}).get("id"):
                            file_id = data["data"]["id"]
                            # Construct download URL
                            download_url = f"https://buzzheavier.com/{file_id}"
                            return {
                                "success": True,
                                "host": "buzzheavier",
                                "download_url": download_url,
                                "filename": filename,
                                "file_size": file_size
                            }
                    except (json.JSONDecodeError, KeyError):
                        pass
                    # Fallback: assume plain text URL (old API format)
                    download_url = text.strip()
                    return {
                        "success": True,
                        "host": "buzzheavier",
                        "download_url": download_url,
                        "filename": filename,
                        "file_size": file_size
                    }
                else:
                    raise FileHostError(f"Upload failed with status {resp.status}: {text}")
        except aiohttp.ClientError as e:
            raise FileHostError(f"Network error during upload: {e}")
        except Exception as e:
            raise FileHostError(f"Upload error: {e}")
        finally:
            file_handle.close()

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


class FileditchUploader:
    """Upload files to new.fileditch.com."""

    BASE_URL = "https://new.fileditch.com/upload.php"
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            headers = {"User-Agent": "VeXL-Bot/1.0"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            # Increase timeout for large file uploads
            timeout = aiohttp.ClientTimeout(total=3600, connect=30)
            self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self.session

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        session = await self._get_session()
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                async with session.request(method, url, **kwargs) as resp:
                    data = await resp.json()
                    return data
            except aiohttp.ClientConnectorError as e:
                last_error = e
                LOGS.warning(f"Connection error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
            except aiohttp.ClientError as e:
                last_error = e
                LOGS.warning(f"HTTP error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
            except asyncio.TimeoutError as e:
                last_error = e
                LOGS.warning(f"Timeout (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
            except Exception as e:
                last_error = e
                LOGS.warning(f"Unexpected error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")

            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))

        raise FileHostError(f"Request failed after {self.MAX_RETRIES} attempts: {last_error}")

    async def upload(self, filepath: str, progress_callback=None) -> Dict[str, Any]:
        """
        Upload a file to new.fileditch.com.

        Args:
            filepath: Path to the file to upload
            progress_callback: Optional async callback(current, total) for progress updates

        Returns:
            Dict with keys: url, filename, size
        """
        session = await self._get_session()

        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)

        # Create multipart form data
        data = aiohttp.FormData()

        # Keep file open until request completes (aiohttp reads lazily)
        file_handle = open(filepath, "rb")
        try:
            data.add_field("file", file_handle, filename=filename)

            # Add token if available (for account uploads)
            if self.token:
                headers = {"Authorization": f"Bearer {self.token}"}
            else:
                headers = {}

            result = await self._request_with_retry("POST", self.BASE_URL, data=data, headers=headers)

            if not result.get("success"):
                error_msg = result.get("message", "Unknown error")
                raise FileHostError(f"Upload failed: {error_msg}")

            download_url = result.get("url")
            returned_filename = result.get("filename")
            returned_size = result.get("size")

            return {
                "success": True,
                "host": "fileditch",
                "download_url": download_url,
                "filename": returned_filename or filename,
                "file_size": returned_size or file_size
            }
        except aiohttp.ClientError as e:
            raise FileHostError(f"Network error during upload: {e}")
        except Exception as e:
            raise FileHostError(f"Upload error: {e}")
        finally:
            file_handle.close()

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


class PixeldrainUploader:
    """Upload files to pixeldrain.com."""

    BASE_URL = "https://pixeldrain.com/api"
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds

    def __init__(self, api_key: str):
        if not api_key:
            raise FileHostError("Pixeldrain API key is required - anonymous uploads are not supported")
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            headers = {"User-Agent": "VeXL-Bot/1.0"}
            # Use Basic Auth with empty username and API key as password
            auth = base64.b64encode(f":{self.api_key}".encode()).decode()
            headers["Authorization"] = f"Basic {auth}"
            # Increase timeout for large file uploads
            timeout = aiohttp.ClientTimeout(total=3600, connect=30)
            self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self.session

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        session = await self._get_session()
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                async with session.request(method, url, **kwargs) as resp:
                    data = await resp.json()
                    return data
            except aiohttp.ClientConnectorError as e:
                last_error = e
                LOGS.warning(f"Connection error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
            except aiohttp.ClientError as e:
                last_error = e
                LOGS.warning(f"HTTP error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
            except asyncio.TimeoutError as e:
                last_error = e
                LOGS.warning(f"Timeout (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
            except Exception as e:
                last_error = e
                LOGS.warning(f"Unexpected error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")

            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))

        raise FileHostError(f"Request failed after {self.MAX_RETRIES} attempts: {last_error}")

    async def upload(self, filepath: str, progress_callback=None) -> Dict[str, Any]:
        """
        Upload a file to pixeldrain.com.

        Args:
            filepath: Path to the file to upload
            progress_callback: Optional async callback(current, total) for progress updates

        Returns:
            Dict with keys: id, download_url, file_size, filename
        """
        session = await self._get_session()

        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)

        # Create multipart form data
        data = aiohttp.FormData()

        # Keep file open until request completes (aiohttp reads lazily)
        file_handle = open(filepath, "rb")
        try:
            data.add_field("file", file_handle, filename=filename)

            result = await self._request_with_retry("POST", f"{self.BASE_URL}/file", data=data)

            if not result.get("success"):
                error_val = result.get("value", "unknown")
                error_msg = result.get("message", "Unknown error")
                raise FileHostError(f"Upload failed: {error_val} - {error_msg}")

            file_id = result.get("id")
            download_url = f"https://pixeldrain.com/api/file/{file_id}"
            info_url = f"https://pixeldrain.com/api/file/{file_id}/info"

            return {
                "success": True,
                "host": "pixeldrain",
                "id": file_id,
                "download_url": download_url,
                "info_url": info_url,
                "file_size": file_size,
                "filename": filename
            }
        except aiohttp.ClientError as e:
            raise FileHostError(f"Network error during upload: {e}")
        except Exception as e:
            raise FileHostError(f"Upload error: {e}")
        finally:
            file_handle.close()

    async def get_info(self, file_id: str) -> Dict[str, Any]:
        """Get file info from pixeldrain."""
        return await self._request_with_retry("GET", f"{self.BASE_URL}/file/{file_id}/info")

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


async def upload_to_filehost(
    filepath: str,
    primary: str = "buzzheavier",
    fallback: str = "fileditch",
    fallback2: str = "pixeldrain",
    progress_callback=None
) -> Dict[str, Any]:
    """
    Upload a file to a file hosting service with fallback chain.

    Args:
        filepath: Path to the file to upload
        primary: Primary host ("buzzheavier", "fileditch", or "pixeldrain")
        fallback: First fallback host ("buzzheavier", "fileditch", or "pixeldrain")
        fallback2: Second fallback host ("buzzheavier", "fileditch", or "pixeldrain")
        progress_callback: Optional async callback(current, total) for progress

    Returns:
        Dict with upload result including download_url

    Raises:
        FileHostError: If all hosts fail
    """
    if not os.path.exists(filepath):
        raise FileHostError(f"File not found: {filepath}")

    file_size = os.path.getsize(filepath)
    LOGS.info(f"Uploading {filepath} ({get_readable_file_size(file_size)}) to {primary}")

    # Check if pixeldrain is configured before attempting
    def get_pixeldrain_key():
        if hasattr(conf, "PIXELDRAIN_API_KEY") and conf.PIXELDRAIN_API_KEY:
            return conf.PIXELDRAIN_API_KEY
        return None

    # Try hosts in order
    hosts_to_try = [primary, fallback, fallback2]

    for i, host in enumerate(hosts_to_try):
        try:
            if host == "buzzheavier":
                uploader = BuzzheavierUploader(conf.BUZZHEAVIER_TOKEN if hasattr(conf, "BUZZHEAVIER_TOKEN") else None)
            elif host == "fileditch":
                uploader = FileditchUploader(conf.FILEDITCH_TOKEN if hasattr(conf, "FILEDITCH_TOKEN") else None)
            elif host == "pixeldrain":
                api_key = get_pixeldrain_key()
                if not api_key:
                    raise FileHostError("Pixeldrain selected but PIXELDRAIN_API_KEY is not configured")
                uploader = PixeldrainUploader(api_key)
            else:
                raise FileHostError(f"Unknown host: {host}")

            result = await uploader.upload(filepath, progress_callback)
            await uploader.close()
            LOGS.info(f"Successfully uploaded to {host}: {result.get('download_url')}")
            return result
        except FileHostError as e:
            LOGS.warning(f"Host {host} failed: {e}")
            if i < len(hosts_to_try) - 1:
                LOGS.info(f"Trying next fallback: {hosts_to_try[i + 1]}")
            continue

    raise FileHostError(f"All hosts failed: {', '.join(hosts_to_try)}")


async def check_file_size_limit(filepath: str) -> Tuple[bool, int]:
    """
    Check if file exceeds Telegram upload limit.

    Args:
        filepath: Path to the file

    Returns:
        Tuple of (exceeds_limit, file_size)
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    file_size = os.path.getsize(filepath)
    limit = getattr(conf, "TELEGRAM_UPLOAD_LIMIT", 2126000000)  # Default 2GB

    return file_size > limit, file_size