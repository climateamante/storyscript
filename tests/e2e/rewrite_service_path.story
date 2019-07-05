http server as client
    when client listen as request
        id = awesome id
        request write content: "https://{app.hostname}/?id={id}\n"
