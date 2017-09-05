#!/usr/bin/python3
import sys
sys.path.insert(0, "/var/www/Opinionated")


from server import app as application

# def application(environ, start_response):
#    status = '200 OK'
#    output = 'Hello World!'

 #   response_headers = [('Content-type', 'text/plain'), ('Content-Length', str(len(output)))]
  #  start_response(status, response_headers)

  #  return [output]
