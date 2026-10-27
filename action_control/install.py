import argparse
import os
from action_control.receiver import install


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    print(install(os.environ["USERNAME"], args.instance, args.version))


if __name__ == "__main__":
    main()
