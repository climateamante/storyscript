logging default
  	when log level: "normal" as logger
  		x = 0
  	when log level: "normal"
  		x = 1
  	when log as logger
  		x = 2
  	when log
  		x = 3
