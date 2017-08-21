import json
import openml
import openmlpimp
import sys

from collections import defaultdict, OrderedDict


def obtain_runids(task_ids, flow_id, classifier, param_templates):
    """
    Obtains relevant run ids from OpenML.

    Parameters
    -------
    task_ids : list[int]
        a list of the relevant task ids

    flow id : int
        the flow id of the optimizer

    classifier : str
        string representation of classifier (not OpenML based)
        for random forest: 'random_forest'

    param_templates : dict[str, dict[str, list]]
        maps from parameter name (sklearn representation) to param grid
        (which is a dict, mapping from parameter name to a list of values)

    Returns
    -------
    results : dict[str, dict[int, dict[mixed, list[ints]]]]
        a dict mapping from parameter name (sklearn representation) to a dict.
        This dict maps from an int (task id) to a dict
        This dict maps from a mixed value (the value of the excluded param) to a list.
        This list contains run ids (ideally 1, but accidently more).
    """
    results = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    setups = openmlpimp.utils.obtain_all_setups(flow=flow_id)

    for task_id in task_ids:
        print("task", task_id)
        try:
            runs = openml.runs.list_runs(task=[task_id], flow=[flow_id])
        except:
            print("runs None")
            continue

        for run_id in runs:
            setup_id = runs[run_id]['setup_id']
            if setup_id not in setups:
                # occurs when experiments are still running.
                sys.stderr.write('setup not available. (should not happen!) %d' %setup_id)
                setups[setup_id] = openml.setups.get_setup(setup_id)

            paramname_paramidx = {param.parameter_name: idx for idx, param in setups[setup_id].parameters.items()}

            for idx, parameter in setups[setup_id].parameters.items():
                if parameter.parameter_name == 'param_distributions':
                    param_grid = json.loads(parameter.value)

                    excluded_params = openmlpimp.utils.get_excluded_params(classifier, param_grid)
                    if len(excluded_params) > 1:
                        continue
                    excluded_param = list(excluded_params)[0]

                    excluded_param_idx = paramname_paramidx[excluded_param.split('__')[-1]]
                    excluded_param_openml = setups[setup_id].parameters[excluded_param_idx]
                    excluded_value = json.loads(excluded_param_openml.value)

                    # TODO: check if legal

                    for name, param_template in param_templates.items():
                        if param_template == param_grid:
                            results[name][task_id][excluded_value].append(run_id)
    return results


def obtain_parameters(classifier):
    return set(obtain_paramgrid(classifier).keys())


def obtain_parameter_combinations(classifier, num_params):
    if num_params != 2:
        raise ValueError('Not implemented yet')
    result = list()
    params = set(obtain_paramgrid(classifier).keys())
    for param1 in params:
        for param2 in params:
            if param1 == param2:
                continue
            result.append([param1, param2])
    return result


def get_excluded_params(classifier, param_grid):
    all_params = obtain_paramgrid(classifier).keys()
    return set(all_params - param_grid)


def get_param_values(classifier, parameter):
    param_grid = obtain_paramgrid(classifier)
    if parameter not in param_grid:
        raise ValueError()
    return param_grid[parameter]


def obtain_paramgrid(classifier, exclude=None, reverse=False):
    if classifier == 'random_forest':
        param_grid = OrderedDict()
        param_grid['classifier__min_samples_leaf'] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        param_grid['classifier__max_features'] = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        param_grid['classifier__bootstrap'] = [True, False]
        param_grid['classifier__min_samples_split'] = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        param_grid['classifier__criterion'] = ['gini', 'entropy']
        param_grid['imputation__strategy'] = ['mean','median','most_frequent']
    else:
        raise ValueError()

    if exclude is not None:
        if isinstance(exclude, str):
            exclude = [exclude]
        for exclude_param in exclude:
            if exclude_param not in param_grid.keys():
                raise ValueError()
            del param_grid[exclude_param]

    if reverse:
        return OrderedDict(reversed(list(param_grid.items())))
    else:
        return param_grid