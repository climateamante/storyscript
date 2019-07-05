http server as s
  when s listen path:"/health" method:"get" as client
  	x = 0
