#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.definitions import ensure_definitions_loaded, get_definition
from feishu.client_registry import GATEWAY_AGENTS
from feishu.channel import FeishuChannel


class IrvingGatewayTests(unittest.TestCase):
    def test_gateway_includes_irving(self) -> None:
        self.assertIn("irving", GATEWAY_AGENTS)

    def test_irving_definition_loads(self) -> None:
        ensure_definitions_loaded()
        definition = get_definition("irving")
        self.assertIsNotNone(definition)
        self.assertEqual(definition.id, "irving")
        self.assertIn("risk.read", definition.capabilities.actions)

    def test_gateway_restarts_one_exited_client_without_stopping_peers(self) -> None:
        class Process:
            created: list["Process"] = []

            def __init__(self, *, name: str, **_kwargs) -> None:
                self.name = name
                self.pid = len(self.created) + 100
                self.exitcode = None
                self._alive = True
                self.created.append(self)

            def start(self) -> None:
                return None

            def join(self, timeout: float = 0) -> None:
                if self.name.endswith("dylan"):
                    self._alive = False
                    self.exitcode = 1
                    return None
                raise KeyboardInterrupt

            def is_alive(self) -> bool:
                return self._alive

            def terminate(self) -> None:
                self._alive = False

        Context = type("Context", (), {"Process": Process})

        channel = FeishuChannel.__new__(FeishuChannel)
        channel.clients = [mock.Mock(agent_id="dylan"), mock.Mock(agent_id="irving")]
        with (
            mock.patch("feishu.channel.multiprocessing.get_context", return_value=Context()),
            mock.patch("feishu.channel.time.sleep"),
        ):
            with self.assertRaises(KeyboardInterrupt):
                channel.start()
        self.assertGreaterEqual(len(Process.created), 3)
        self.assertTrue(any(proc.name.endswith("irving") for proc in Process.created))


if __name__ == "__main__":
    unittest.main()
