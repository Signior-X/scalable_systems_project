from time import sleep
from flask import Flask, jsonify, request
import os
import requests

app = Flask(__name__)

# stores the list of instances that are currently working
WORKING_INSTANCES = set()
WORKING_WORKERS = set()


def test_instance(instance_url):
    ''' Makes a get request to the instance url, and return True if it is working '''
    print("Testing instance url: ", instance_url)

    try:
        requests.get(instance_url)
    except requests.exceptions.InvalidSchema:
        try:
            requests.get("https://" + str(instance_url))
        except requests.exceptions.SSLError:
            requests.get("http://" + str(instance_url))
        except:
            return False

    except requests.ConnectionError:
        return False

    return True

def handle_instance_failure(instance_id):
    # check if it is in the working instances or not
    # If it is, there is a failure
    # If not, it has been deleted by the job_manager already, nothing to do

    if instance_id not in WORKING_INSTANCES:
        print("Worker should be completed, instance already deleted")
    else:
        print("Instance with id", instance_id, " failed")
        WORKING_INSTANCES.remove(instance_id)
        print("Instane has been failed, create a new instance!")
        # TODO


def create_worker(instance_id):
    ''' Returns True if creation of worker proxy is successfull '''
    try:
        fork_id = os.fork()
    except:
        return False

    if fork_id > 0:
        WORKING_WORKERS.add(instance_id)
        return True
    else:
        print("Child process and id is : ", os.getpid())

        # Now we will keep making some requests
        while True:
            if not test_instance(instance_id):
                # Worker with instance_id failed
                break
            sleep(3)

        print("Worker ", instance_id, " completed or failed")
        WORKING_WORKERS.remove(instance_id)
        handle_instance_failure(instance_id)


def create_instance():
    # 1. Will make a request to resource manager
    # 2. Update WORKING_INSTANCES
    # 3. Creates a Worker
    # Returns a tuple(Success_Status, instance_id or error)

    instance_id = "localhost:5001"  # TODO

    WORKING_INSTANCES.add(instance_id)
    if not create_worker(instance_id):
        return False, "Worker Creation Failed!"

    return True, instance_id


def delete_instance():
    # Will make a request to resource manager
    # 2. Update the WORKING_INSTANCES
    # 3. Worker will be already deleted as it will throw error
    return True


@app.route('/')
def index_page():
    ''' Returns the list of working instances '''
    return jsonify(WORKING_INSTANCES=str(WORKING_INSTANCES), WORKING_WORKERS=str(WORKING_WORKERS))


@app.route('/test_instance')
def test_instance_api():
    if "instance_url" not in request.args:
        return jsonify(success=False, error="instance_url not provided")

    instance_url = request.args["instance_url"]

    response = "Request failed to " + \
        str(instance_url) + ", Instance is not working!"
    if test_instance(instance_url):
        response = "Successful Request " + \
            str(instance_url) + ", Instance is working!"

    return jsonify(success=True, response=response)


@app.route('/create_instance')
def create_instance_api():
    # Make a request to the resource manager to create an instance
    # and then start the worker proxy that looks over to that instance

    success_status, instance_or_error = create_instance()
    if success_status:
        return jsonify(success=True, instance_id=instance_or_error)

    return jsonify(success=False, error=instance_or_error)


@app.route('/create_worker')
def create_worker_api():
    if "instance_id" not in request.args:
        return jsonify(success=False, error="instance_id not provieded!")

    instance_id = request.args["instance_id"]
    print(instance_id)

    if create_worker(instance_id):
        return jsonify(success=True, created=True)
    else:
        return jsonify(success=False, error="Worker creation failed!")


if __name__ == "__main__":
    app.run(debug=True)
