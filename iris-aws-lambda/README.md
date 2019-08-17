# iris-aws-lambda


Running the server locally:

```
sam local start-api -n env.json
```

Making a query locally:
```
curl -d "{\"url\":\"https://s3.amazonaws.com/cdn-origin-etr.akc.org/wp-content/uploads/2017/11/16105011/English-Cocker-Spaniel-Slide03.jpg\"}" \
    -H "Content-Type: application/json" \
    -X POST http://localhost:3000/invocations
  ```


package for Deploy
```
sam package \
    --output-template-file packaged.yaml \
    --s3-bucket iris-ai
```

Deploy
```
aws cloudformation deploy --template-file ./packaged.yaml --stack-name iris-dev --capabilities CAPABILITY_IAM
```

Get url
```
aws cloudformation describe-stacks --stack-name iris-dev --query 'Stacks[].Outputs[?OutputKey==`PyTorchApi`]' --output table
```    

Get logs
```
sam logs -n PyTorchFunction --stack-name iris-dev --tail
```

Delete Deploy
```
aws cloudformation delete-stack --stack-name iris-dev
```
