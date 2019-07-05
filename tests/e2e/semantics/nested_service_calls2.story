http server as client
    when client listen method:"get" path:"/" as request
        a = (request fetch url:"foo-url") + (request fetch url:"bar-url")
