import json
import os
import re
import zipfile

from mineai.constants import PACK_FORMATS
from mineai.io_utils import atomic_write_text


class PackWriter:
    """Creates resource pack and datapack zip handles for translated assets."""

    def __init__(
        self,
        mc_dir: str,
        pack_base_name: str,
        mc_version: str,
        lang_name: str,
    ) -> None:
        self.mc_dir = mc_dir
        self.rp_zip_path: str | None = None
        self.dp_zip_path: str | None = None
        self.rp_handle: zipfile.ZipFile | None = None
        self.dp_handle: zipfile.ZipFile | None = None
        self.written: set[str] = set()
        self.rp_written = False
        self.dp_written = False
        self.resourcepack_enabled = False
        fmt = PACK_FORMATS.get(mc_version, PACK_FORMATS["1.21.1"])

        rp_dir = os.path.join(mc_dir, "resourcepacks")
        dp_dir = os.path.join(mc_dir, "config", "openloader", "data")
        os.makedirs(rp_dir, exist_ok=True)
        os.makedirs(dp_dir, exist_ok=True)

        safe_name = re.sub(r'[\\/*?:"<>|]', "", pack_base_name.strip() or "MineAI_Pack")
        if not safe_name.lower().endswith(".zip"):
            safe_name += ".zip"

        try:
            self.rp_zip_path = self._unique_path(rp_dir, safe_name)
            self._create_zip(
                self.rp_zip_path,
                fmt["rp"],
                f"{os.path.basename(self.rp_zip_path)} - MineAI",
            )
            self.rp_handle = zipfile.ZipFile(
                self.rp_zip_path,
                "a",
                compression=zipfile.ZIP_DEFLATED,
            )

            dp_name = os.path.basename(self.rp_zip_path).replace(
                ".zip",
                "_Datapack.zip",
            )
            self.dp_zip_path = self._unique_path(dp_dir, dp_name)
            self._create_zip(
                self.dp_zip_path,
                fmt["dp"],
                f"{dp_name} - MineAI",
            )
            self.dp_handle = zipfile.ZipFile(
                self.dp_zip_path,
                "a",
                compression=zipfile.ZIP_DEFLATED,
            )
        except Exception:
            self._cleanup_partial_archives()
            raise

    @staticmethod
    def _unique_path(directory: str, filename: str) -> str:
        path = os.path.join(directory, filename)
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(filename)
        counter = 1
        while True:
            candidate = os.path.join(directory, f"{base}_{counter}{ext}")
            if not os.path.exists(candidate):
                return candidate
            counter += 1

    @staticmethod
    def _create_zip(path: str, pack_format: int, description: str) -> None:
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "pack.mcmeta",
                json.dumps({"pack": {"pack_format": pack_format, "description": description}}, indent=2),
            )

    def handle_for_path(self, internal_path: str) -> zipfile.ZipFile | None:
        if internal_path.lower().startswith("data/"):
            return self.dp_handle
        return self.rp_handle

    def write(self, internal_path: str, data: bytes) -> None:
        handle = self.handle_for_path(internal_path)
        if handle and internal_path not in self.written:
            handle.writestr(internal_path, data)
            self.written.add(internal_path)
            if internal_path.lower().startswith("data/"):
                self.dp_written = True
            else:
                self.rp_written = True

    @staticmethod
    def _validate_zip(path: str | None) -> None:
        if not path:
            return
        with zipfile.ZipFile(path, "r") as archive:
            bad_entry = archive.testzip()
            if bad_entry is not None:
                raise zipfile.BadZipFile(
                    f"CRC check failed for {bad_entry} in {path}"
                )

    def _close_handles(self) -> list[Exception]:
        errors: list[Exception] = []
        for attribute in ("rp_handle", "dp_handle"):
            handle = getattr(self, attribute)
            if handle is None:
                continue
            try:
                handle.close()
            except Exception as exc:
                errors.append(exc)
            finally:
                setattr(self, attribute, None)
        return errors

    def _remove_output_archives(self) -> None:
        for path in (self.rp_zip_path, self.dp_zip_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def _cleanup_partial_archives(self) -> None:
        self._close_handles()
        self._remove_output_archives()

    def abort(self) -> None:
        """Close and remove archives created by an incomplete translation job."""
        self._cleanup_partial_archives()

    def close(self) -> tuple[str | None, str | None]:
        errors = self._close_handles()
        for path_attribute, has_payload in (
            ("rp_zip_path", self.rp_written),
            ("dp_zip_path", self.dp_written),
        ):
            path = getattr(self, path_attribute)
            if not has_payload:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError as exc:
                        errors.append(exc)
                setattr(self, path_attribute, None)
        if not errors:
            for path in (self.rp_zip_path, self.dp_zip_path):
                try:
                    self._validate_zip(path)
                except Exception as exc:
                    errors.append(exc)
                    break
        if errors:
            self._remove_output_archives()
            raise errors[0]
        if self.rp_zip_path:
            self.resourcepack_enabled = self._enable_resource_pack(
                self.rp_zip_path
            )
        return self.rp_zip_path, self.dp_zip_path

    def _enable_resource_pack(self, resourcepack_path: str) -> bool:
        """Add the generated pack to options.txt after existing lower priorities."""
        options_path = os.path.join(self.mc_dir, "options.txt")
        if not os.path.isfile(options_path):
            return False
        try:
            with open(options_path, encoding="utf-8-sig", newline="") as handle:
                content = handle.read()
            match = re.search(
                r"(?m)^resourcePacks:(\[[^\r\n]*\])(?=\r?$)", content
            )
            if not match:
                return False
            selected = json.loads(match.group(1))
            if not isinstance(selected, list) or not all(
                isinstance(value, str) for value in selected
            ):
                return False
            pack_id = f"file/{os.path.basename(resourcepack_path)}"
            selected = [value for value in selected if value != pack_id]
            selected.append(pack_id)
            replacement = "resourcePacks:" + json.dumps(
                selected, ensure_ascii=False
            )
            updated = content[: match.start()] + replacement + content[match.end() :]
            if updated != content:
                atomic_write_text(options_path, updated)
            return True
        except (OSError, ValueError, TypeError):
            return False
