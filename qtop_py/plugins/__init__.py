from qtop_py.plugins.demo import DemoBatchSystem
from qtop_py.plugins.oar import OARBatchSystem
from qtop_py.plugins.pbs import PBSBatchSystem
from qtop_py.plugins.sge import SGEBatchSystem
from qtop_py.plugins.slurm import SlurmBatchSystem

__all__ = ["oar", "pbs", "sge", "slurm", "demo"]

PLUGIN_BATCH_SYSTEMS = (DemoBatchSystem, OARBatchSystem, PBSBatchSystem, SGEBatchSystem, SlurmBatchSystem)


def node_job_ids(node):
    jobs = set(node["core_job_map"].values())
    for plugin in PLUGIN_BATCH_SYSTEMS:
        if plugin.node_job_id_field:
            jobs.update(node.get(plugin.node_job_id_field, []))
    return jobs


def node_state_symbol(node):
    for plugin in PLUGIN_BATCH_SYSTEMS:
        symbol = plugin.node_state_symbol(node)
        if symbol:
            return symbol
    return ""
