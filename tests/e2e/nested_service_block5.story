websocket accept path:"/" as ws
  when ws message as client
	  foo = client.data.foo
	  when ws listen filter:foo as event
		break
