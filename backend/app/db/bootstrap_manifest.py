from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BootstrapScript:
    key: str
    script_type: str
    file_path: Path
    description: str


PROJECT_ROOT = Path(__file__).resolve().parents[3]

BOOTSTRAP_SCRIPTS = [
    BootstrapScript(
        key="001_recruitment_system_mssql_schema",
        script_type="schema",
        file_path=PROJECT_ROOT / "scripts" / "001_recruitment_system_mssql_schema.sql",
        description="Creates and updates the core MSSQL schema.",
    ),
    BootstrapScript(
        key="002_seed_master_data",
        script_type="seed-core",
        file_path=PROJECT_ROOT / "scripts" / "002_seed_master_data.sql",
        description="Seeds master and reference data.",
    ),
    BootstrapScript(
        key="003_seed_permissions_and_role_mappings",
        script_type="seed-core",
        file_path=PROJECT_ROOT / "scripts" / "003_seed_permissions_and_role_mappings.sql",
        description="Seeds permissions, admin access, and starter role templates.",
    ),
    BootstrapScript(
        key="004_seed_sample_business_data",
        script_type="seed-sample",
        file_path=PROJECT_ROOT / "scripts" / "004_seed_sample_business_data.sql",
        description="Seeds sample business data for development and verification.",
    ),
]


def select_bootstrap_scripts(include_sample_data: bool = False) -> list[BootstrapScript]:
    return [
        script
        for script in BOOTSTRAP_SCRIPTS
        if include_sample_data or script.script_type != "seed-sample"
    ]

