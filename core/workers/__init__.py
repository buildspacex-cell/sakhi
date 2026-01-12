"""Worker registry for orchestration helpers (lab/dev)."""

from typing import Callable, Dict, Any

from core.workers.elemental.elemental_stm_worker import run_elemental_stm_worker
from core.workers.elemental.elemental_weekly_worker import run_elemental_weekly_worker
from core.workers.elemental.elemental_monthly_worker import run_elemental_monthly_worker
from core.workers.elemental.personal_model_elemental_worker import run_personal_model_elemental_worker
from core.workers.energy.energy_weekly_worker import run_energy_weekly_worker
from core.workers.energy.energy_monthly_worker import run_energy_monthly_worker
from core.workers.energy.personal_model_energy_worker import run_personal_model_energy_worker
from core.workers.signals.neutral_signal_extraction_worker import run_neutral_signal_extraction_worker

WORKER_REGISTRY: Dict[str, Callable[..., Any]] = {
    "neutral_signal_extraction": run_neutral_signal_extraction_worker,
    "elemental_stm": run_elemental_stm_worker,
    "elemental_weekly": run_elemental_weekly_worker,
    "elemental_monthly": run_elemental_monthly_worker,
    "personal_model_elemental": run_personal_model_elemental_worker,
    "energy_weekly": run_energy_weekly_worker,
    "energy_monthly": run_energy_monthly_worker,
    "personal_model_energy": run_personal_model_energy_worker,
}
