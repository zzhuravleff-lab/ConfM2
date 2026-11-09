@echo off
for %%f in (configs\test\*.yaml) do (
    echo --- %%f
    python src\main.py --config %%f
)
