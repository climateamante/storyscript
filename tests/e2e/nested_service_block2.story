logging default
	when logging level: "normal" as logger
		x = 0
	http server
		when listen path:"/health" method:"get" as client
			x = 1
	when logging as logger
		x = 2
