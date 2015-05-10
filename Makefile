.PHONY : all run

all : run

run :
	python main.py | tee output.log

.PHONY : all
