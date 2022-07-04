.PHONY : all
all: deploy
deployHomolog:
	./package.sh
	npx serverless deploy --stage homolog

deployProduction:
	./package.sh
	npx serverless deploy --stage production