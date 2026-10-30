# SPDX-License-Identifier: MIT

from types import SimpleNamespace

import pytest

from qtop_py import plugins, qtop
from qtop_py.serialiser import GenericBatchSystem


class CustomBatchSystem(GenericBatchSystem):
    detection_priority = 10
    optional_input_files = {"details": "details.txt"}
    node_job_id_field = "custom_job_ids"

    @staticmethod
    def get_mnemonic():
        return "custom"

    @staticmethod
    def queue_is_blocked(state):
        return state == "paused"

    @staticmethod
    def configure_command(name, command, options):
        return command + " --include-hidden" if name == "nodes" and not options.SOURCEDIR else command

    @staticmethod
    def node_state_symbol(node):
        return node.get("custom_state_symbol", "")

    @staticmethod
    def snapshot_notes(metadata):
        return ["Custom snapshot incomplete."] if metadata.get("custom_missing") else []


@pytest.fixture
def custom_plugin(monkeypatch):
    registry = qtop.PLUGIN_BATCH_SYSTEMS + (CustomBatchSystem,)
    monkeypatch.setattr(qtop, "PLUGIN_BATCH_SYSTEMS", registry)
    monkeypatch.setattr(plugins, "PLUGIN_BATCH_SYSTEMS", registry)
    monkeypatch.setattr(qtop, "scheduler", "custom", raising=False)


def test_custom_plugin_controls_queue_states_and_detection(custom_plugin, monkeypatch):
    assert qtop.queue_is_blocked("paused", "custom")
    assert not qtop.queue_is_blocked("D", "custom")
    monkeypatch.setattr(qtop.shutil, "which", lambda command: "/bin/" + command)
    config = {"signature_commands": {"pbs": "pbsnodes", "custom": "custom-nodes"}}
    assert qtop.auto_get_avail_batch_system(config) == "custom"


def test_custom_plugin_controls_commands_and_optional_inputs(custom_plugin, monkeypatch, tmp_path):
    options = SimpleNamespace(SOURCEDIR=None, ALL_PARTITIONS=True, workdir=str(tmp_path))
    config = {"schedulers": {"custom": {"nodes": "%(savepath)s/nodes.txt, custom-nodes"}}, "savepath": str(tmp_path)}
    commands = qtop.finalize_filepaths_schedulercommands(options, config)
    assert commands["nodes"][1] == "custom-nodes --include-hidden"

    options.SOURCEDIR = str(tmp_path)
    monkeypatch.setattr(qtop, "args", options, raising=False)
    nodes = tmp_path / "nodes.txt"
    nodes.write_text("node1")
    details = tmp_path / "details.txt"
    details.write_text("allocation details")
    inputs = {"nodes": (str(nodes), "unused"), "details": (str(tmp_path / "missing.txt"), "unused")}
    assert qtop.get_input_filenames(inputs, config) == {"nodes": str(nodes), "details": str(details)}
    details.unlink()
    assert qtop.get_input_filenames(inputs, config) == {"nodes": str(nodes)}


def test_custom_plugin_preserves_jobs_without_cpu_placement_and_state_marker(custom_plugin):
    node = {"core_job_map": {"0": "1"}, "custom_job_ids": ["1", "2"], "custom_state_symbol": "!"}
    assert qtop.WNOccupancy._count_jobs_strict([node]) == 2
    assert plugins.node_state_symbol(node) == "!"
    cluster = qtop.Cluster.__new__(qtop.Cluster)
    cluster._calculate_jobs_per_node({"node1": node})
    assert node["node_job_set"] == {"1", "2"}


def test_custom_plugin_supplies_snapshot_diagnostics(custom_plugin, monkeypatch, capsys):
    config = {"user_display_parts": []}
    monkeypatch.setattr(qtop, "config", config, raising=False)
    document = SimpleNamespace(_snapshot_metadata={"custom_missing": 1})
    options = SimpleNamespace(WATCH=False, ANONYMIZE=True, STRICTCHECK=False, sect_1_off=False, sect_2_off=False, sect_3_off=False)
    display = qtop.TextDisplay(document, config, None, None, None, options)
    display.display_selected_sections("", "", "")
    assert capsys.readouterr().out == "Custom snapshot incomplete.\n"
