#!/bin/bash

# get controller' ids
function  get_hosts () {
    fuel nodes | grep controller | awk '{print $1}'
}

CONTROLLER_IDS=$(get_hosts)
RALLY_SCENARIOS="
lots_of_small.yaml
increasing_resources.yaml
nested_test_resource.yaml
"

function execute_script () {
    SCRIPT="$@"
    for ID in ${CONTROLLER_IDS} ; do
        ssh node-${ID} "${SCRIPT}"
    done
}

function execute_script_once () {
    SCRIPT="$@"
    for ID in ${CONTROLLER_IDS} ; do
        ssh node-${ID} "${SCRIPT}"
        break
    done
}

# count number of CPU 
function count_proc_num () {
    NUM_PROC_SCRIPT="grep -c ^processor /proc/cpuinfo"
    execute_script_once ${NUM_PROC_SCRIPT}
}

function set_num_engine_workers () {
    KEY="num_engine_workers"
    HEAT_CONF="/etc/heat/heat.conf"
    VALUE=$1
    REPLACE_VALUE="sed -i 's/\($KEY *= *\).*/\1$VALUE/' $HEAT_CONF"
    execute_script ${REPLACE_VALUE}
}

function restart_heat_engine () {
#    RESTART_ENGINE="crm resource restart clone_p_heat-engine"
    RESTART_ENGINE="service heat-engine restart"
    execute_script ${RESTART_ENGINE}
}

function restart_heat_api () {
    RESTART_API="service heat-api restart"
    execute_script ${RESTART_API}
}


function set_up_convergence () {
    HEAT_CONF="/etc/heat/heat.conf"
    REMOVE_PREVIOUS_CONVERGENCE="if grep convergence_engine $HEAT_CONF; then sed -i /convergence_engine/d $HEAT_CONF; fi"
    execute_script ${REMOVE_PREVIOUS_CONVERGENCE}
    # if you want to enable convergence - uncomment line below
#    SET_CONVERGENCE_TRUE="sed -i 's/^\[DEFAULT\]/[DEFAULT]\nconvergence_engine = True\n/' $HEAT_CONF"
#    execute_script ${SET_CONVERGENCE_TRUE}
    restart_heat_engine
    restart_heat_api
}

function start_rally () {
    for scen in ${RALLY_SCENARIOS}; do
        id=`rally task start $scen --tag convergence-$1 | grep -e "Task .*: finished" | awk '{print$2}' | sed "s/:$//"`
        # safe results
        rally task results $id > results/new_default/$scen-$1.json
        rally task report $id --out results/new_default/$scen-$1.html
    done
}

function check_rally_scenarios () {
    for scen in ${RALLY_SCENARIOS}; do
        if [[ ! -f $scen ]] ; then
            echo "File $scen is not exist"
            exit 1
        fi
    done
}

function main () {
    check_rally_scenarios
    set_up_convergence
    for workers_num in `seq $1 $3 $2`; do
        # set new count of engines
        set_num_engine_workers $workers_num
        # restart engine service
        restart_heat_engine
        # wait some time before testing
        sleep 1
        start_rally $workers_num
    done
}


# Script should get two parameters
# MIN_ENGINE and MAX_ENGINE
set -- `getopt -n$0 -u -a --longoptions="max: min: step:" "h" "$@"` || usage
[ $# -eq 0 ] && usage

while [ $# -gt 0 ]
do
    case "$1" in
       --min)
            min=$2
            shift
            ;;
       --max)
            max=$2
            shift
            ;;
       --step)
            step=$2
            shift
            ;;
       -h)
           echo "Default values for paramaters 'max=8', 'min=4', 'step=1' for number of engines" >&2
           ;;
       --)
           shift
           break
           ;;
       \?) 
           echo "Invalid option: -$OPTARG" >&2
           break;;
    esac
    shift
done

if [[ -z ${max} ]] ; then
  max=8
fi

if [[ -z ${min} ]] ; then
  min=4
fi

if [[ -z ${step} ]] ; then
  step=1
fi

main ${min} ${max} ${step}
