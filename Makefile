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


