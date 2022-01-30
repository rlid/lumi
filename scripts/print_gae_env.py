import sys

import yaml

with open("app_env_var.yaml", "r") as stream:
    try:
        env_vars = yaml.safe_load(stream).get("env_variables")
        for name, value in env_vars.items():
            if len(sys.argv) == 1:
                print(f"{name}={value}")
            else:
                if sys.argv[1] == 'fish':
                    print(f"set -x {name} {value}")
                else:
                    print(f"{sys.argv[1]} {name}={value}")
    except yaml.YAMLError as e:
        print(e)
