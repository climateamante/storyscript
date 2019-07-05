http server as client
    when client listen method:"get" path:"/" as request
        request write content:"Hello world!"
