# /// script
# requires-python = ">=3.11"
# dependencies = ["camas>=0.1.30"]
# ///
"""Project tasks — the single source of truth for local dev and CI.

Run with ``camas`` (or, standalone, ``uv run tasks.py <task>``). This file
replaces ``Taskfile.yml`` and the per-crate command lists duplicated in
``.github/workflows/packages.yml``: the per-crate clippy/build/test commands
now live once, here, so CI and a local ``camas check`` run exactly the same
thing. ``camas ci --github-matrix=tasks`` emits the crate axis for the GitHub
Actions matrix, so the crate list also lives once.

Toolchain, targets and feature combinations mirror ``packages.yml`` verbatim
so ``camas check`` reproduces that workflow. Contract checks (``contracts.yml``)
stay behind their existing ``devtools/`` scripts, invoked here as leaves.
"""

import platform
import sys

from camas import Claude, Config, Parallel, Sequential, Task, run_cli

TOOLCHAIN = "1.82.0"  # packages.yml TOOLCHAIN_STABLE
CARGO = f"cargo +{TOOLCHAIN}"
COSMWASM_CHECK_VERSION = "3.0.9"  # last released cosmwasm-check before 3.1.0, for the contracts leaf


def crate(name: str, *cargo_args: str, env: dict[str, str] | None = None) -> Sequential:
    """A crate's CI job: its cargo steps, in order, under a named task."""
    return Sequential(*(Task(f"{CARGO} {args}", env=env or {}) for args in cargo_args), name=name)


fmt = Task(f"{CARGO} fmt", mutates=True)
fmt_check = Task(f"{CARGO} fmt -- --check", name="fmt-check")

cosmwasm_core = crate(
    "cosmwasm-core",
    "clippy -p cosmwasm-core --all-targets -- -D warnings",
    "clippy -p cosmwasm-core --all-features --all-targets -- -D warnings",
    "build -p cosmwasm-core --locked",
    "build -p cosmwasm-core --locked --release --lib --target wasm32-unknown-unknown",
    "build -p cosmwasm-core --locked --release --lib --target thumbv7em-none-eabi",
    "build -p cosmwasm-core --locked --no-default-features",
    "build -p cosmwasm-core --locked --no-default-features --release --lib --target wasm32-unknown-unknown",
    "build -p cosmwasm-core --locked --no-default-features --release --lib --target thumbv7em-none-eabi",
    "build -p cosmwasm-core --locked --all-features",
    "build -p cosmwasm-core --locked --all-features --release --lib --target wasm32-unknown-unknown",
    "build -p cosmwasm-core --locked --all-features --release --lib --target thumbv7em-none-eabi",
    "test -p cosmwasm-core --locked --no-default-features",
    "test -p cosmwasm-core --locked --all-features",
)

cosmwasm_crypto = crate(
    "cosmwasm-crypto",
    "clippy -p cosmwasm-crypto --all-targets -- -D warnings",
    "build -p cosmwasm-crypto --locked",
    "test -p cosmwasm-crypto --locked",
)

cw_schema = crate(
    "cw-schema",
    "clippy -p cw-schema --all-targets -- -D warnings",
    "build -p cw-schema --locked",
    "test -p cw-schema --locked",
)

cw_schema_derive = crate(
    "cw-schema-derive",
    "clippy -p cw-schema-derive --all-targets -- -D warnings",
    "build -p cw-schema-derive --locked",
    "test -p cw-schema-derive --locked",
)

cosmwasm_derive = crate(
    "cosmwasm-derive",
    "clippy -p cosmwasm-derive --all-targets -- -D warnings",
    "build -p cosmwasm-derive --locked",
    "test -p cosmwasm-derive --locked",
)

cosmwasm_schema = crate(
    "cosmwasm-schema",
    "clippy -p cosmwasm-schema --all-targets -- -D warnings",
    "build -p cosmwasm-schema --locked",
    "test -p cosmwasm-schema --locked",
)

cosmwasm_schema_derive = crate(
    "cosmwasm-schema-derive",
    "clippy -p cosmwasm-schema-derive --all-targets -- -D warnings",
    "build -p cosmwasm-schema-derive --locked",
    "test -p cosmwasm-schema-derive --locked",
)

cosmwasm_std = crate(
    "cosmwasm-std",
    "clippy -p cosmwasm-std --all-targets -- -D warnings",
    "clippy -p cosmwasm-std --all-targets --features std,iterator,staking,stargate -- -D warnings",
    "clippy -p cosmwasm-std --all-features --all-targets -- -D warnings",
    "build -p cosmwasm-std --locked",
    "build -p cosmwasm-std --locked --release --lib --target wasm32-unknown-unknown",
    "build -p cosmwasm-std --locked --no-default-features --features std",
    "build -p cosmwasm-std --locked --no-default-features --features std --release --lib --target wasm32-unknown-unknown",
    "build -p cosmwasm-std --locked --features std,iterator,staking,stargate,cosmwasm_1_2",
    "build -p cosmwasm-std --locked --features std,iterator,staking,stargate,cosmwasm_1_2 --release --lib --target wasm32-unknown-unknown",
    "build -p cosmwasm-std --locked --all-features",
    "build -p cosmwasm-std --locked --all-features --release --lib --target wasm32-unknown-unknown",
    "test -p cosmwasm-std --locked",
    "test -p cosmwasm-std --locked --no-default-features --features std",
    "test -p cosmwasm-std --locked --features std,iterator,staking,stargate,cosmwasm_1_2",
    "test -p cosmwasm-std --locked --all-features",
)

vm_steps = [
    Task(f"{CARGO} {args}")
    for args in (
        "clippy -p cosmwasm-vm --all-targets --no-default-features -- -D warnings",
        "clippy -p cosmwasm-vm --all-targets --features iterator,staking,stargate -- -D warnings",
        "build -p cosmwasm-vm --locked",
        "build -p cosmwasm-vm --locked --features iterator,staking,stargate",
        "build -p cosmwasm-vm --locked --all-features",
        "test -p cosmwasm-vm --locked",
        "test -p cosmwasm-vm --locked --features iterator,staking,stargate",
        "test -p cosmwasm-vm --locked --all-features",
    )
]
on_native_linux = sys.platform.startswith("linux") and "microsoft" not in platform.uname().release.lower()
if on_native_linux:
    vm_steps.append(Task(f"{CARGO} build --locked --example multi_threaded_cache"))
    vm_steps.append(
        Task(("bash", "-c", "time target/debug/examples/multi_threaded_cache > /dev/null"))
    )
cosmwasm_vm = Sequential(*vm_steps, name="cosmwasm-vm")

cosmwasm_vm_derive = crate(
    "cosmwasm-vm-derive",
    "clippy -p cosmwasm-vm-derive --all-targets -- -D warnings",
    "build -p cosmwasm-vm-derive --locked",
    "test -p cosmwasm-vm-derive --locked",
)

# NO_COLOR: camas colorizes leaf output; cosmwasm-check's test asserts on the uncolored form.
cosmwasm_check = crate(
    "cosmwasm-check",
    "clippy -p cosmwasm-check --all-targets -- -D warnings",
    "build -p cosmwasm-check --locked",
    "test -p cosmwasm-check --locked",
    env={"NO_COLOR": "1"},
)

CRATES = (
    cosmwasm_core,
    cosmwasm_crypto,
    cw_schema,
    cw_schema_derive,
    cosmwasm_derive,
    cosmwasm_schema,
    cosmwasm_schema_derive,
    cosmwasm_std,
    cosmwasm_vm,
    cosmwasm_vm_derive,
    cosmwasm_check,
)

check = Parallel(fmt_check, *CRATES)

ci = Parallel(*CRATES)

install_cosmwasm_check = Sequential(
    Task(f"{CARGO} install cosmwasm-check@{COSMWASM_CHECK_VERSION} --locked --force"),
    Task(("bash", "-c", "mv ~/.cargo/bin/cosmwasm-check ~/.cargo/bin/cosmwasm-check-released")),
    Task(f"{CARGO} install --path ./packages/check --locked --force"),
    name="install-cosmwasm-check",
)
contracts = Sequential(
    install_cosmwasm_check,
    Task("./devtools/check-contracts.sh parallel", when="contracts"),
)
update_schemas = Task("./devtools/update-schemas.sh", name="update-schemas", when="contracts")
cov = Sequential(
    Task(f"{CARGO} llvm-cov clean"),
    Task(f"{CARGO} llvm-cov --workspace --no-cfg-coverage"),
)

_ = Config(default_task=check, github_task=check, agent=Claude(fix=fmt, check=check))

if __name__ == "__main__":
    run_cli(globals())
