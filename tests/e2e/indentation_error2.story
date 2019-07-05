http server as client
    when client listen method:"get" path:"/" as request
    	h = hashes digest method: "sha1" data: "foo"
        request write content:h
