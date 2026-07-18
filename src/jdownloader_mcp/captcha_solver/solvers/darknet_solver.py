"""
DarkNet/YOLO Solver - Integration with cracker0dks/CaptchaSolver.
=================================================================
Wraps the cracker0dks CaptchaSolver (YOLO DarkNet neural network)
for solving geometric and text captchas from hosters like:
- keep2share.cc / k2s.cc
- fileboom.me / fboom.me
- tezfiles.com
- publish2.me
- filejoker.net
- depositfiles.com / dfiles.eu

This solver can work in two modes:
1. INTEGRATED: Detects if CaptchaSolver is installed inside JDownloader
   and lets JD use it automatically (no action needed from MCP).
2. STANDALONE: Runs the DarkNet inference directly from this module
   using the weights and config from CaptchaSolver.

Setup (standalone mode):
    1. Download darknet binary for your platform
    2. Download the YOLO weights from CaptchaSolver releases
    3. Configure paths in the solver config

Setup (integrated mode):
    1. Install CaptchaSolver into your JDownloader folder
       (copy 'JDownloader 2.0/tools/offlineCaptchaSolver/' to your JD install)
    2. Restart JDownloader — it auto-detects and solves captchas

GitHub: https://github.com/cracker0dks/CaptchaSolver
"""

import os
import io
import json
import logging
import subprocess
import tempfile
from typing import Optional

from ..base import BaseSolver, CaptchaChallenge, CaptchaSolution, CaptchaType
from ..preprocessing import ImageProcessor

logger = logging.getLogger("captcha-solver.darknet")


class DarkNetSolver(BaseSolver):
    """
    Solves captchas using YOLO DarkNet (cracker0dks/CaptchaSolver approach).

    Config options:
        mode: "standalone" or "integrated" (default: "standalone")
        darknet_path: Path to darknet executable
        weights_path: Path to YOLO .weights file
        config_path: Path to YOLO .cfg file
        data_path: Path to .data file (class names)
        jd_tools_path: Path to JDownloader's tools/offlineCaptchaSolver/
        node_path: Path to node executable (default: "node")
        confidence_threshold: Minimum detection confidence (default: 0.5)
    """

    name = "darknet_yolo"
    supported_types = [CaptchaType.TEXT_IMAGE, CaptchaType.GEOMETRIC]

    # Known hosters that cracker0dks supports
    SUPPORTED_HOSTERS = [
        "keep2share", "k2s.cc", "fileboom", "fboom",
        "tezfiles", "publish2", "filejoker", "depositfiles", "dfiles",
    ]

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)

        self.mode = self.config.get("mode", "standalone")
        self.darknet_path = self.config.get("darknet_path", "")
        self.weights_path = self.config.get("weights_path", "")
        self.config_path = self.config.get("config_path", "")
        self.data_path = self.config.get("data_path", "")
        self.jd_tools_path = self.config.get("jd_tools_path", "")
        self.node_path = self.config.get("node_path", "node")
        self.confidence_threshold = self.config.get("confidence_threshold", 0.5)

        # Validate setup
        if self.mode == "standalone":
            if not self._validate_standalone():
                logger.info(
                    "DarkNet solver: standalone mode not configured. "
                    "Set darknet_path, weights_path, config_path, data_path."
                )
                self.enabled = False
        elif self.mode == "integrated":
            if not self._validate_integrated():
                logger.info(
                    "DarkNet solver: JDownloader CaptchaSolver not found. "
                    "Install from: https://github.com/cracker0dks/CaptchaSolver"
                )
                self.enabled = False

    def _validate_standalone(self) -> bool:
        """Check if standalone DarkNet is properly configured."""
        if not self.darknet_path or not os.path.exists(self.darknet_path):
            return False
        if not self.weights_path or not os.path.exists(self.weights_path):
            return False
        if not self.config_path or not os.path.exists(self.config_path):
            return False
        return True

    def _validate_integrated(self) -> bool:
        """Check if cracker0dks CaptchaSolver is installed in JDownloader."""
        if not self.jd_tools_path:
            # Try common JDownloader paths
            common_paths = [
                os.path.expanduser("~/.jd/tools/offlineCaptchaSolver"),
                os.path.expanduser("~/.var/app/org.jdownloader.JDownloader/data/jdownloader/tools/offlineCaptchaSolver"),
                "/Applications/JDownloader 2.0/tools/offlineCaptchaSolver",
                "C:\\JDownloader 2.0\\tools\\offlineCaptchaSolver",
            ]
            for path in common_paths:
                if os.path.exists(path):
                    self.jd_tools_path = path
                    return True
            return False
        return os.path.exists(self.jd_tools_path)

    def can_solve(self, challenge: CaptchaChallenge) -> bool:
        """Check if this solver supports the given challenge's hoster."""
        if not super().can_solve(challenge):
            return False

        # Only solve for known supported hosters
        hoster = challenge.hoster.lower()
        return any(h in hoster for h in self.SUPPORTED_HOSTERS)

    def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """Solve captcha using DarkNet YOLO detection."""
        if self.mode == "standalone":
            return self._solve_standalone(challenge)
        elif self.mode == "integrated":
            return self._solve_integrated(challenge)
        else:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error=f"Unknown mode: {self.mode}",
            )

    def _solve_standalone(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """
        Run DarkNet detection directly on the captcha image.
        Saves image to temp file, runs darknet detect, parses output.
        """
        # Get image
        img = self._get_image(challenge)
        if img is None:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error="Failed to load captcha image",
            )

        try:
            # Save image to temp file
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                temp_path = f.name
                img.save(f, format="JPEG")

            # Run darknet detection
            cmd = [
                self.darknet_path,
                "detect",
                self.config_path,
                self.weights_path,
                temp_path,
                "-thresh", str(self.confidence_threshold),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Parse darknet output
            # Format: "X: 99%\nY: 98%\n..."
            text, confidence = self._parse_darknet_output(result.stdout)

            # Cleanup
            os.unlink(temp_path)

            if text:
                return CaptchaSolution(
                    success=True,
                    solution=text,
                    solver_name=self.name,
                    confidence=confidence,
                )
            else:
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error=f"DarkNet detected nothing. Output: {result.stdout[:200]}",
                )

        except subprocess.TimeoutExpired:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error="DarkNet timeout (>30s)",
            )
        except FileNotFoundError:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error=f"DarkNet binary not found: {self.darknet_path}",
            )
        except Exception as e:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error=f"DarkNet error: {e}",
            )

    def _solve_integrated(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """
        Use the cracker0dks Node.js solver script directly.
        This calls the same scripts that JDownloader uses.
        """
        img = self._get_image(challenge)
        if img is None:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error="Failed to load captcha image",
            )

        try:
            # Determine which script to use based on hoster
            hoster = challenge.hoster.lower()
            script_name = self._get_solver_script(hoster)

            if not script_name:
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error=f"No CaptchaSolver script for hoster: {challenge.hoster}",
                )

            script_path = os.path.join(self.jd_tools_path, script_name)
            if not os.path.exists(script_path):
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error=f"Script not found: {script_path}",
                )

            # Save image to temp file
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                temp_path = f.name
                img.save(f, format="JPEG")

            # Run Node.js solver script
            cmd = [self.node_path, script_path, temp_path]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.jd_tools_path,
            )

            os.unlink(temp_path)

            # Parse output (scripts print the solution to stdout)
            solution_text = result.stdout.strip()

            if solution_text and result.returncode == 0:
                return CaptchaSolution(
                    success=True,
                    solution=solution_text,
                    solver_name=self.name,
                    confidence=0.9,
                )
            else:
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error=f"Script returned: stdout='{solution_text}', stderr='{result.stderr[:200]}'",
                )

        except subprocess.TimeoutExpired:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error="CaptchaSolver script timeout (>60s)",
            )
        except Exception as e:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error=f"Integrated solver error: {e}",
            )

    def _get_solver_script(self, hoster: str) -> str:
        """Map hoster to the appropriate cracker0dks solver script."""
        if "keep2share" in hoster or "k2s" in hoster:
            return "solve_keep2share.js"
        elif "fileboom" in hoster or "fboom" in hoster:
            return "solve_keep2share.js"  # Same captcha type
        elif "tezfiles" in hoster:
            return "solve_keep2share.js"
        elif "publish2" in hoster:
            return "solve_keep2share.js"
        elif "filejoker" in hoster:
            return "solve_filejoker.js"
        elif "depositfiles" in hoster or "dfiles" in hoster:
            return "solve_keep2share.js"
        return ""

    def _parse_darknet_output(self, output: str) -> tuple:
        """
        Parse darknet detection output.
        Format example:
            temp.jpg: Predicted in 74.892000 milli-seconds.
            e: 99%
            h: 74%
            C: 100%
            Y: 99%
        """
        lines = output.strip().split("\n")
        chars = []
        total_conf = 0

        for line in lines:
            line = line.strip()
            # Match pattern: "X: 99%" or "X: 99" (character: confidence)
            if ":" in line and "%" in line:
                parts = line.split(":")
                if len(parts) == 2:
                    char = parts[0].strip()
                    try:
                        conf_str = parts[1].strip().replace("%", "")
                        conf = int(conf_str) / 100.0
                        if len(char) == 1 and conf >= self.confidence_threshold:
                            chars.append((char, conf))
                            total_conf += conf
                    except ValueError:
                        continue

        if not chars:
            return "", 0.0

        # Sort by x-position would be ideal, but darknet outputs in detection order
        # For now, use the order they appear
        text = "".join(c for c, _ in chars)
        avg_conf = total_conf / len(chars)

        return text, avg_conf

    def _get_image(self, challenge: CaptchaChallenge):
        """Extract PIL Image from challenge."""
        if challenge.image_data:
            return ImageProcessor.from_bytes(challenge.image_data)
        elif challenge.image_base64:
            return ImageProcessor.from_base64(challenge.image_base64)
        return None

    @staticmethod
    def install_instructions() -> str:
        """Return setup instructions for cracker0dks/CaptchaSolver."""
        return """
=== CaptchaSolver Installation (cracker0dks) ===

Option A: Integrated with JDownloader (auto-solves without MCP):
  1. Download latest release: https://github.com/cracker0dks/CaptchaSolver/releases
  2. Extract 'JDownloader 2.0/' content into your JD2 folder
  3. Restart JDownloader

Option B: Standalone (for MCP solver):
  1. Install Node.js
  2. git clone https://github.com/cracker0dks/CaptchaSolver
  3. cd CaptchaSolver/JDownloader\\ 2.0/tools/offlineCaptchaSolver && npm install
  4. Download DarkNet: https://github.com/AlexeyAB/darknet/releases
  5. Configure solver:
     config = {
         "mode": "standalone",
         "darknet_path": "/path/to/darknet",
         "weights_path": "/path/to/captcha.weights",
         "config_path": "/path/to/captcha.cfg",
         "data_path": "/path/to/captcha.data",
     }

Supported hosters:
  - keep2share.cc / k2s.cc
  - fileboom.me / fboom.me
  - tezfiles.com / publish2.me
  - filejoker.net
  - depositfiles.com / dfiles.eu
"""
