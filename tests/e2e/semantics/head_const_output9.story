http server as server
    when server listen path: "/" as req
        text = req.body["a"]["b"]
        if text == "a"
            text = "b"
        else
            text = "c"
