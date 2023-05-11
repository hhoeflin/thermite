SHELL := /bin/bash

.ONESHELL:

MAKEFILE_DIR=$(realpath $(dir $(firstword $(MAKEFILE_LIST))))

CONDA_ENV:=${MAKEFILE_DIR}/.conda_env
REPO_NAME:=thermite

# ENVIRONMENT
create-base-env:
	mamba env create --prefix ${CONDA_ENV} --file conda_env.yaml
	mamba run --prefix ${CONDA_ENV} flit install -s

lock-env:
	mamba env export --prefix ${CONDA_ENV} | grep -v ${REPO_NAME} > conda_env.lock.yaml

create-lock-env:
	mamba env create --prefix ${CONDA_ENV} --file conda_env.lock.yaml
	mamba run --prefix ${CONDA_ENV} flit install -s

########################
# Run the examples
########################
run-examples: run-examples-basics run-examples-dataclass run-examples-lists run-examples-advanced

run-examples-basics:
	myrun(){ echo "> $$@"; eval $$@; };
	myrun python examples/basics/adjust_help.py --help > examples/basics/adjust_help.out
	myrun python examples/basics/opts_to_args.py --help > examples/basics/opts_to_args.out

run-examples-dataclass:
	myrun(){ echo "> $$@"; eval $$@; };
	myrun python examples/dataclasses/basic.py --help > examples/dataclasses/basic.out
	myrun python examples/dataclasses/with_arguments.py --help > examples/dataclasses/with_arguments.out
	myrun python examples/dataclasses/custom_converter.py --help > examples/dataclasses/custom_converter.out

run-examples-lists:
	myrun(){ echo "> $$@"; eval $$@; };
	myrun python examples/lists/default.py --help > examples/lists/default_help.out
	myrun python examples/lists/default.py --x 1 --x 2 > examples/lists/default_output.out
	myrun python examples/lists/var_length_list_opt.py --x 1 2 3 > examples/lists/var_length_list_opt_output.out
	myrun python examples/lists/var_length_list_opt.py --help > examples/lists/var_length_list_opt_help.out
	myrun python examples/lists/multiple_args.py 1 2 3 --0 4 5 > examples/lists/multiple_args_output.out
	myrun python examples/lists/multiple_args.py --help > examples/lists/multiple_args_help.out
	myrun python examples/lists/empty_list.py --x-empty --y 4 --y 5 > examples/lists/empty_list_output.out
	myrun python examples/lists/empty_list.py --help > examples/lists/empty_list_help.out

run-examples-advanced:
	myrun(){ echo "> $$@"; eval $$@; };
	myrun python examples/adv/param_transfer.py --help > examples/adv/param_transfer_help.out
	myrun python examples/adv/param_transfer.py --input-dir foo --param1 bar --param2 0.5 > examples/adv/param_transfer_output.out
	myrun python examples/adv/config_file.py --defaults-file examples/adv/config_file.yml#version1 --help > examples/adv/config_file_help.out
