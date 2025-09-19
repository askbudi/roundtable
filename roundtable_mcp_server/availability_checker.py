#!/usr/bin/env python3
"""CLI Availability Checker for Roundtable MCP Server.

This module checks the availability of CLI tools and saves the results to a JSON file
for use by the MCP server to determine which tools to enable.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default path for storing availability check results
DEFAULT_ROUNDTABLE_DIR = Path.home() / ".roundtable"
AVAILABILITY_FILE = "availability_check.json"


class CLIAvailabilityChecker:
    """Checks availability of CLI tools and manages the availability cache."""

    def __init__(self, roundtable_dir: Optional[Path] = None):
        """Initialize the availability checker.

        Args:
            roundtable_dir: Directory to store availability results. Defaults to ~/.roundtable
        """
        self.roundtable_dir = roundtable_dir or DEFAULT_ROUNDTABLE_DIR
        self.availability_file = self.roundtable_dir / AVAILABILITY_FILE

        # Ensure the roundtable directory exists
        self.roundtable_dir.mkdir(exist_ok=True)

    async def check_codex_availability(self) -> Dict[str, Any]:
        """Check if Codex CLI is available."""
        try:
            proc = await asyncio.create_subprocess_shell(
                "codex --help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                return {
                    "available": True,
                    "status": "✅ Codex CLI Available",
                    "last_checked": datetime.now().isoformat(),
                    "error": None
                }
            else:
                return {
                    "available": False,
                    "status": f"❌ Codex CLI failed with exit code {proc.returncode}",
                    "last_checked": datetime.now().isoformat(),
                    "error": stderr.decode() if stderr else None
                }
        except Exception as e:
            return {
                "available": False,
                "status": f"❌ Codex CLI error: {str(e)}",
                "last_checked": datetime.now().isoformat(),
                "error": str(e)
            }

    async def check_claude_availability(self) -> Dict[str, Any]:
        """Check if Claude Code CLI is available."""
        try:
            proc = await asyncio.create_subprocess_shell(
                "claude --help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                return {
                    "available": True,
                    "status": "✅ Claude Code CLI Available",
                    "last_checked": datetime.now().isoformat(),
                    "error": None
                }
            else:
                return {
                    "available": False,
                    "status": f"❌ Claude Code CLI failed with exit code {proc.returncode}",
                    "last_checked": datetime.now().isoformat(),
                    "error": stderr.decode() if stderr else None
                }
        except Exception as e:
            return {
                "available": False,
                "status": f"❌ Claude Code CLI error: {str(e)}",
                "last_checked": datetime.now().isoformat(),
                "error": str(e)
            }

    async def check_cursor_availability(self) -> Dict[str, Any]:
        """Check if Cursor Agent CLI is available."""
        try:
            proc = await asyncio.create_subprocess_shell(
                "cursor --help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                return {
                    "available": True,
                    "status": "✅ Cursor CLI Available",
                    "last_checked": datetime.now().isoformat(),
                    "error": None
                }
            else:
                return {
                    "available": False,
                    "status": f"❌ Cursor CLI failed with exit code {proc.returncode}",
                    "last_checked": datetime.now().isoformat(),
                    "error": stderr.decode() if stderr else None
                }
        except Exception as e:
            return {
                "available": False,
                "status": f"❌ Cursor CLI error: {str(e)}",
                "last_checked": datetime.now().isoformat(),
                "error": str(e)
            }

    async def check_gemini_availability(self) -> Dict[str, Any]:
        """Check if Gemini CLI is available."""
        try:
            proc = await asyncio.create_subprocess_shell(
                "gemini --help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                return {
                    "available": True,
                    "status": "✅ Gemini CLI Available",
                    "last_checked": datetime.now().isoformat(),
                    "error": None
                }
            else:
                return {
                    "available": False,
                    "status": f"❌ Gemini CLI failed with exit code {proc.returncode}",
                    "last_checked": datetime.now().isoformat(),
                    "error": stderr.decode() if stderr else None
                }
        except Exception as e:
            return {
                "available": False,
                "status": f"❌ Gemini CLI error: {str(e)}",
                "last_checked": datetime.now().isoformat(),
                "error": str(e)
            }

    async def check_all_availability(self) -> Dict[str, Dict[str, Any]]:
        """Check availability of all CLI tools."""
        logger.info("Starting CLI availability check...")

        # Check all CLIs in parallel
        results = await asyncio.gather(
            self.check_codex_availability(),
            self.check_claude_availability(),
            self.check_cursor_availability(),
            self.check_gemini_availability(),
            return_exceptions=True
        )

        cli_names = ["codex", "claude", "cursor", "gemini"]
        availability_results = {}

        for cli_name, result in zip(cli_names, results):
            if isinstance(result, Exception):
                availability_results[cli_name] = {
                    "available": False,
                    "status": f"Exception during check: {str(result)}",
                    "last_checked": datetime.now().isoformat(),
                    "error": str(result)
                }
            else:
                availability_results[cli_name] = result

        # Add metadata
        availability_results["_metadata"] = {
            "check_timestamp": datetime.now().isoformat(),
            "checker_version": "1.0.0",
            "total_checked": len(cli_names),
            "available_count": sum(1 for r in availability_results.values()
                                 if isinstance(r, dict) and r.get("available", False))
        }

        return availability_results

    def save_availability_results(self, results: Dict[str, Dict[str, Any]]) -> None:
        """Save availability results to JSON file."""
        try:
            with open(self.availability_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Availability results saved to: {self.availability_file}")
        except Exception as e:
            logger.error(f"Failed to save availability results: {e}")
            raise

    def load_availability_results(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Load availability results from JSON file."""
        try:
            if not self.availability_file.exists():
                logger.warning(f"Availability file not found: {self.availability_file}")
                return None

            with open(self.availability_file, 'r') as f:
                results = json.load(f)

            logger.info(f"Loaded availability results from: {self.availability_file}")
            return results
        except Exception as e:
            logger.error(f"Failed to load availability results: {e}")
            return None

    def get_available_clis(self) -> List[str]:
        """Get list of available CLI tools from cached results."""
        results = self.load_availability_results()
        if not results:
            logger.warning("No availability results found, returning empty list")
            return []

        available_clis = []
        for cli_name, cli_data in results.items():
            if cli_name.startswith("_"):  # Skip metadata
                continue
            if isinstance(cli_data, dict) and cli_data.get("available", False):
                available_clis.append(cli_name)

        logger.info(f"Available CLIs from cache: {available_clis}")
        return available_clis

    async def perform_availability_check(self, save_results: bool = True) -> Dict[str, Dict[str, Any]]:
        """Perform a complete availability check and optionally save results.

        Args:
            save_results: Whether to save results to the JSON file

        Returns:
            Dictionary with availability results for each CLI
        """
        results = await self.check_all_availability()

        if save_results:
            self.save_availability_results(results)

        return results

    def print_availability_report(self, results: Dict[str, Dict[str, Any]]) -> None:
        """Print a formatted availability report."""
        print("\n" + "="*60)
        print("🔍 CLI AVAILABILITY REPORT")
        print("="*60)

        metadata = results.get("_metadata", {})
        if metadata:
            print(f"📅 Check time: {metadata.get('check_timestamp', 'Unknown')}")
            print(f"📊 Total CLIs checked: {metadata.get('total_checked', 0)}")
            print(f"✅ Available: {metadata.get('available_count', 0)}")
            print()

        for cli_name, cli_data in results.items():
            if cli_name.startswith("_"):  # Skip metadata
                continue

            if not isinstance(cli_data, dict):
                continue

            available = cli_data.get("available", False)
            status_icon = "✅" if available else "❌"

            print(f"{status_icon} {cli_name.upper()}")
            print(f"   Status: {cli_data.get('status', 'Unknown')}")

            if cli_data.get("error"):
                print(f"   Error: {cli_data['error']}")

            print()

        print(f"💾 Results saved to: {self.availability_file}")
        print("="*60)


async def main():
    """Main entry point for CLI availability checking."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check availability of CLI tools for Roundtable MCP Server"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Perform availability check and save results"
    )
    parser.add_argument(
        "--roundtable-dir",
        type=Path,
        default=DEFAULT_ROUNDTABLE_DIR,
        help=f"Directory to store results (default: {DEFAULT_ROUNDTABLE_DIR})"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to file (just print)"
    )

    args = parser.parse_args()

    if not args.check:
        parser.print_help()
        return

    checker = CLIAvailabilityChecker(args.roundtable_dir)

    try:
        results = await checker.perform_availability_check(save_results=not args.no_save)
        checker.print_availability_report(results)

        # Exit with appropriate code
        metadata = results.get("_metadata", {})
        available_count = metadata.get("available_count", 0)

        if available_count == 0:
            print("⚠️  No CLI tools are available!")
            sys.exit(1)
        else:
            print(f"🎉 {available_count} CLI tool(s) available and ready to use!")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Availability check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())