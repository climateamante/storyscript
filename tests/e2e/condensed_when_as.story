http server as my_server
  when listen path:"/health" method:"get" as client
  	x = 0
