# token-imbalances

This script is to calculate the raw token imbalances before and after a settlement.
The raw token imbalances are stored in the raw_token_imbalances table.
Additionally, coingecko prices for fetchable token addresses at the time of transaction are stored in the coingecko_prices table. These tables are a part of the Solver Slippage Database.
These prices can be used to convert raw imbalances to ETH.

## Env Setup
Install pyenv so you can manage different versions of python on your machine:
```sh
brew install pyenv
```

Then once pyenv is install properly you should install python 3.10.16 or greater.

```sh
pyenv install 3.10.16
```
There will need to be some env variables that you need to set like `CHAIN_SLEEP_TIME`, you can set those in a .env file. View the sample .env.sample file to see what you might need to set. 

Then run `pyenv local 3.10.16` this will set the local env in your shell to this vesion, you can then proceed with the next set up instructions:

**Set up virtual environment:**
```sh
python -m venv .venv
source .venv/bin/activate
```

**Install requirements from root directory:**
```bash
pip install -r requirements.txt
```

**Environment Variables**: Make sure the `.env` file is correctly set up locally. You can use the `.env.sample` file as reference.

**To fetch imbalances for a single transaction hash, run:**
```bash
python -m src.imbalances_script
```

**To run a daemon for checking imbalances, run the following from the root directory:**

```bash
python -m src.daemon
```

## Tests
*Note: Make sure docker is installed and the daemon is running so you can execute this* 

To build and start a local database for testing use the command
```sh
docker build -t test_db_image -f Dockerfile.test_db .
docker run -d --name test_db_container -p 5432:5432 -v ${PWD}/database/00_legacy_tables.sql:/docker-entrypoint-initdb.d/00_legacy_tables.sql -v ${PWD}/database/01_table_creation.sql:/docker-entrypoint-initdb.d/01_table_creation.sql test_db_image

```

To run the unittests you can use the make target unittest `make unittest`, however you might have a couple issues:
- You might run into the issue of the binary package for psycopg not being installed simply run:
```sh
pip install "psycopg[binary,pool]"
```

To shutdown the docker test db and remove the image/container you can do:

```sh
	docker stop test_db_container || true
	docker rm test_db_container || true
	docker rmi test_db_image || true
```

## Using the Makefile

You can do all of the above also by running the make commands:

```sh
make install

make imbalances

make test_db

make stop_test_db

make unittest
```
