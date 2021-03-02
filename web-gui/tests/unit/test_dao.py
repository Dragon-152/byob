import pytest
from hashlib import md5
from random import getrandbits
from datetime import datetime
from buildyourownbotnet import app, db, bcrypt
from buildyourownbotnet.core import dao
from buildyourownbotnet.models import User, Payload, Session, Task, ExfiltratedFile
from ..conftest import new_user, new_session

def test_get_sessions(new_user):
    """
    Given a user, 
    when dao.get_sessions is called,
    check that user sessions are returned from the database correctly.
    """
    # check for valid user
    assert len(dao.get_sessions(new_user.id)) == 0

    # check for invalid user
    assert len(dao.get_sessions(-1)) == 0
    
def test_get_sessions_new(new_session):
    """
    Given a user,
    when the dao.get_sessions_new is called,
    check the user's new sessions are fetched and their 'new' attribute is updated to false in the database.
    """
    # get session owner (user)
    user_query = User.query.filter_by(username=new_session.owner)
    user = user_query.first()
    assert user is not None

    # get users's new sessions and test 'new' attribute has been toggled to false
    new_user_sessions = dao.get_sessions_new(user.id)
    assert len(new_user_sessions) > 0
    assert all(s.new is False for s in user.sessions)
    
def test_handle_session(new_user):
    """
    Given a new user,
    when a new user is created via dao.handle_session function,
    then check the session metadata is stored in the database correctly. 
    """
    # add test session (without uid)
    uid = md5(bytes(getrandbits(10))).hexdigest()
    input_session_dict = {
			"online": True,
			"joined": datetime.utcnow(),
			"last_online": datetime.utcnow(),
			"public_ip": '1.2.3.4',
			"local_ip": '192.1.1.168',
			"mac_address": '00:0A:95:9D:68:16',
			"username": 'test_user',
			"administrator": True,
			"platform": 'linux2',
			"device": 'test_device',
			"architecture": 'x32',
			"latitude": 0.00,
			"longitude": 0.00,
			"owner": new_user.username,
    }
    try:
        output_session_dict = dao.handle_session(input_session_dict)
    except Exception as e:
        pytest.fail("dao.handle_session exception handling new session: " + str(e))

    # check server assigned uid
    assert 'uid' in output_session_dict
    uid = output_session_dict['uid'] 

    # run tests
    session_query = Session.query.filter_by(uid=uid)
    assert len(session_query.all()) == 1

    session = session_query.first()
    assert session.owner == new_user.username
    assert session.uid == uid
    assert session.online is True
    assert (datetime.utcnow() - session.joined).seconds <= 5
    assert (datetime.utcnow() - session.last_online).seconds <= 5
    assert session.public_ip == '1.2.3.4'
    assert session.local_ip == '192.1.1.168'
    assert session.mac_address == '00:0A:95:9D:68:16'
    assert session.username == 'test_user'
    assert session.administrator is True
    assert session.platform == 'linux2'
    assert session.device == 'test_device'
    assert session.architecture == 'x32'
    assert session.longitude == 0.00
    assert session.latitude == 0.00

    # add test session (with uid)
    uid = md5(bytes(getrandbits(10))).hexdigest()
    input_session_dict = {
			"uid": uid,
			"online": True,
			"joined": datetime.utcnow(),
			"last_online": datetime.utcnow(),
			"public_ip": '5.6.7.8',
			"local_ip": '192.1.1.168',
			"mac_address": '00:0A:95:9D:68:16',
			"username": 'test_user',
			"administrator": True,
			"platform": 'linux2',
			"device": 'test_device',
			"architecture": 'x32',
			"latitude": 0.00,
			"longitude": 0.00,
			"owner": new_user.username,
    }
    try:
        output_session_dict = dao.handle_session(input_session_dict)
    except Exception as e:
        pytest.fail("dao.handle_session exception handling existing session: " + str(e))

    # run tests
    session_query = Session.query.filter_by(uid=uid)
    assert len(session_query.all()) == 1

    session = session_query.first()
    assert session.owner == new_user.username
    assert session.uid == uid
    assert session.online is True
    assert (datetime.utcnow() - session.joined).seconds <= 5
    assert (datetime.utcnow() - session.last_online).seconds <= 5
    assert session.public_ip == '5.6.7.8'
    assert session.local_ip == '192.1.1.168'
    assert session.mac_address == '00:0A:95:9D:68:16'
    assert session.username == 'test_user'
    assert session.administrator is True
    assert session.platform == 'linux2'
    assert session.device == 'test_device'
    assert session.architecture == 'x32'
    assert session.longitude == 0.00
    assert session.latitude == 0.00
    
def test_handle_task(new_session):
    """
    Given a session,
    when the dao.handle_task method is called from a session,
    check 3 scenarios:
    
    1. A new task is issued a UID, an issued timestamp, 
    and the metadata is stored in the database correctly.

    2. A completed task has the result stored in the database, and
    is marked as completed.

    3. An invalid task is handled without exception or error.
    """
    # 1. test new task
    input_task_dict = {
        "session": new_session.uid,
        "task": "whoami",
    }
    try:
        output_task_dict = dao.handle_task(input_task_dict)
    except Exception as e:
        pytest.fail("dao.handle_task exception handling new task: " + str(e))

    # run tests
    task_query = Task.query.filter_by(session=new_session.uid)
    assert len(task_query.all()) == 1

    task = task_query.first()
    assert len(task.uid) == 32
    assert task.session == new_session.uid
    assert task.task == 'whoami'
    assert (datetime.utcnow() - task.issued).seconds <= 2
    
    # 2. test completed task
    output_task_dict['result'] = 'test_result'
    try:
        completed_task_dict = dao.handle_task(output_task_dict)
    except Exception as e:
        pytest.fail("dao.handle_task exception handling completed task: " + str(e))

    # run tests
    task_query = Task.query.filter_by(session=new_session.uid)
    assert len(task_query.all()) == 1

    task = task_query.first()
    assert task.result == 'test_result'
    assert task.completed is not None
    assert (datetime.utcnow() - task.completed).seconds <= 5

    # 3. test invalid task
    try:
        invalid_task_dict = dao.handle_task('invalid task - not a dict')
    except Exception as e:
        pytest.fail("dao.handle_task exception handling invalid task: " + str(e))
    assert isinstance(invalid_task_dict, dict)
    assert 'result' in invalid_task_dict
    assert 'Error' in invalid_task_dict['result']
    
def test_update_session_status(new_session):
    """
    Given a session,
    when the dao.update_session_status is called,
    check that the 'online' attribute of session metadata is correctly updated in the database.
    """
    # toggle online/offline status
    prev_status = new_session.online
    new_status = False if new_session.online else True 
    dao.update_session_status(new_session.uid, new_status)

    # check if it was updated correctly
    session_query = Session.query.filter_by(uid=new_session.uid)
    session = session_query.first()
    assert session is not None
    assert session.online == new_status

    