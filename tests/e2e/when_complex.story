http server
	when listen as li
		break
	when listen path:"/foo"
		break
	when listen path:"/foo" as li
		break

http server as serv
	when serv listen
    	break
	when serv listen as sa
		break
	when serv listen path:"/foo"
		break
	when serv listen path:"/foo" as li
		break
