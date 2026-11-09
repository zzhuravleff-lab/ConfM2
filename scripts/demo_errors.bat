@echo off
for %%f in (configs\errors\*.yaml) do (
    echo --- %%f
    python src\main.py --config %%f
)
echo --- nonexistent.yaml
python src\main.py --config nonexistent.yaml
