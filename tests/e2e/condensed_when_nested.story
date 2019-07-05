items = [0]
http server
  foreach items as item
  	when listen path:"/health" method:"get" as client
  		x = 0
