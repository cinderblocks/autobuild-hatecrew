#!/bin/bash

echo_service_message()
{
  sleep 0.1
  echo "##teamcity[$@]" 1>&2
}

record_event()
{
  local message=$(echo "$1" | sed -e "s/|/||/g; s/'/|'/g")
  echo_service_message message text="'${message}'"
}

begin_section()
{
  echo_service_message blockOpened name="'$1'"
}

end_section()
{
  echo_service_message blockClosed name="'$1'"
}

set -e
if [ "x${TEAMCITY_PROJECT_NAME}" != "x" ]
then
    begin_section "VirtualEnv install nose"
    virtualenv py_install_wrapper
    . py_install_wrapper/bin/activate
    pip install pyparsing==1.5.7
    pip install pydot
    pip install nose
    pip install llbase
    end_section "VirtualEnv install nose"
fi

begin_section "Self Test"
if nosetests -v
then
    echo_service_message buildStatus text="'Self Test Passed'" status="'SUCCESS'"
    ExitStatus=0
else
    echo_service_message buildStatus text="'Self Test Failed'" status="'FAILURE'"
fi
end_section "Self Test"

exit $ExitStatus