# Workload scoring for pmem with cadvisor

- [Workload scoring for pmem with cadvisor](#workload-scoring-for-pmem-with-cadvisor)
  - [How](#how)
    - [Algorithm](#algorithm)
    - [Prerequisites](#prerequisites)
      - [Deployed workloads](#deployed-workloads)
      - [Workload identification](#workload-identification)
      - [Behavior measurement](#behavior-measurement)
      - [Requirement measurement](#requirement-measurement)
    - [Implementation](#implementation)
      - [Infra description](#infra-description)
        - [Workloads](#workloads)
        - [Monitoring](#monitoring)
          - [kube-state-metrics](#kube-state-metrics)
          - [cadvisor](#cadvisor)
      - [Rules](#rules)

This document provides an overlook on how to benchmark an application to assess its possible performance gains using Intel® Optane™ DC Persistent memory. Although the implementation is based on Prometheus rules deployed as operator, concepts and algorithm should be translatable to other systems.

## How

The description provided is based on Prometheus, but the algorithm and part of requirements apply to any system.

### Algorithm

As mentioned in the beginning, the overall goal of the process is to determine if a workload is a good fit for 2LM (Memory mode) node with Intel memory. In general, it answers the question:

*Which will be saturated first on a node with Intel memory dice: memory or any other resource?*

The answer takes form of ratio how many times faster will the other resource (cpu, memory bandwidth or working set size) be saturated than the memory, for example if score is 1.25 it means that one of the resources will saturate 1.25 times faster than memory. Therefore score interpretation is the following:

| Score | Interpretation|
| -----| --------------|
|0 | workload which almost do not use any resources apart from allocating memory, perfect match for 2LM (Memory mode) |
| <1| node filled with such workloads, memory will be 100% utilized when constrained by other resource|
| <3 | not perfect but still worth considering as good candidate for 2LM node|
|>>3 | memory utilization will be low because of saturation on other resources|

As mentioned, algorithm looks at 4 different parameters:

- CPU requirements
- Memory requirements
- Memory bandwidth
- Working set size

Score computation depends on couple of parameters describing applications access to memory:

1. *How much memory does it require?* (the more the better)
2. *How much of this memory is actually used most of the time (what is the WSS (working set size))?* (the smaller the better)
3. *What bandwidth does the app require in communication between CPU cache and memory?* (the bigger the better)
4. *How often does the app reach to memory outside the CPU cache?*

*NOTE*: In the case of the algorithm, the scope of data is the whole application, not a certain container or a certain pod.

Based on the data gathered answering those questions, algorithm works as follows:

1. Prepare an entry that mocks existence of a PMEM node with some assumed parameters, as it will be required for comparison
2. Measure application instances behavior
3. Aggregate data to represent overall application behavior
4. Assess the most problematic limitation that will be returned as the score

The whole point of the implementation provided as example later on is to prepare all the data required by 5 operations: 3 to get ratio of requirements of cpu, bandwidth and wss in relation to memory, then normalizing it based on the mock pmem node and returnig the max (so the worst possible) score.

### Prerequisites

List of concepts and requirements to know before implementation explanation.

#### Deployed workloads

The algorithm assumes that it is used in production or production-like environment. For the best results input shouldn't be a synthetic workload, but a normal aplication.

#### Workload identification

The algorithm requires that there will be a way to identify all instances of a workload. E.g. a common label on all pods identifying the workload they belong to (see how "app" label is handled in example). In the case, that there is no uniform, common label available across many workloads, one can use built-in controllers labels like controler hash revision. You can also relay on labels if you follow [recommended labels](https://kubernetes.io/docs/concepts/overview/working-with-objects/common-labels/#labels).

#### Behavior measurement

Shift to cAdvisor has been made, however if one requires, they can use a different software. It has to be able to report memory bandwidth based on resctrl, perf events, specifically offcore_requests.demand_data_rd and offcore_requests.demand_rfo, as well as working set size based on /proc/smaps file. Fortunately cAdvisor can do this all.

*WARNING*: as of today some changes required for full readiness are still awaiting to be merged. For now, [this fork and branch](https://github.com/wacuuu/cadvisor/tree/jwalecki/even-more-magic) contains all needed features.

#### Requirement measurement

Besides measuring application behavior, one must take the requirements into consideration, namely requirement for CPU and memory. This can be easily done by using kube-state-metrics. If this is not possible, one can manually apply the requirements, although it would require to put them for every benchmarked application.

### Implementation

The following part describes how is the example in this repo implemented.

#### Infra description

Example consists of example workloads and monitoring setup.

##### Workloads

Workloads used by us in internal testing are located in [this directory](../../workloads). Only thing important for notice is the **app** label with value set to workload name. It is used to identify the workload in rules as mentioned in introduction.

##### Monitoring

Deployment consist of 3 independent parts: cadvisor, Prometheus and kube-state-metrics.

###### kube-state-metrics

Nothing particularly important in this part of deployment. All the details are [here](../kube-state-metrics). It is set up in such a way that it is accessible for Prometheus deployed as operator.

###### cadvisor

Deployment as daemonset is defined in [cadvisor directory](../cadvisor). As suggested before, this is using a custom stitched cadvisor docker image, so one must provide it. Two aspects stand out: perf config and binary arguments. As for the perf config, [perf-hmem-cascadelake.json](../cadvisor/perf-hmem-cascadelake.json) is used. Although it contains a bit more than required, it is good for this deployment. On the arguments:

- `--perf_events_config=/etc/config/perf-hmem-cascadelake.json` is an argument pointing to perf config, listing needed perf events
- `--v=6` increases verbosity in logs. Especially useful when deploying for the first time, as it will for example make understanding why some perf events don't work
- `--disable_metrics=advtcp,process,sched,hugetlb,cpu_topology,tcp,udp,percpu,accelerator,disk,diskIO,network` overwrite the default value for this parameter to include referenced memory
- `--port=9101` port to expose the metric, has to be consistent with the rest of deployment definition
- `--referenced_read_interval=20s` the interval with which the referenced bytes are counted. As this is a CPU intensive operation due to kernel behavior, this may require prolonging
- `--referenced_reset_interval=120s` the interval with which the referenced bytes are restored to 0 state. This is required to assess how big the working set is over time of application operation
- `--store_container_labels=true` this is required to be able to later identify which container belongs to which.
- `--raw_cgroup_prefix_whitelist=kubepods` this limits the amount of containers monitored by cadvisor

Besides that, deployment adds service monitoring to Prometheus.

#### Rules

All rules needed for algorithm to work are contained in following rule files: 

- [../prometheusrules.score.yaml](../prometheusrules.score.yaml) 
- [./cadvisor/prometheusrules.cadvisor-$TYPE.yaml](./cadvisor) if **cadvisor** used as monitoring agent

where **$TYPE** is one of the following:
- **app** - aggregate individual container metrics (requirements) into pods and apps
- **node-pmem** - virtual PMEM node for score classification ("virtual node capacity")
- **node** - dynamic onlie node classification for score classification ("node capacity")
- **wss** - aggregate individual container metrics (requirements) applications "working set size" requirement


File "prometheusrules.$TYPE-node-pmem" describes mock pmem node with parameters derived from documentation, which are later used to assess the score.

FIXME: Below information is outdated!
TODO: Update below docs with new sections names and new file names after reorganization.

The rest rules files contains all the operations needed to prepare data for score computation. The first part, `reference-node-scoring`, takes the data describing mock pmem node and builds and entry for later comparation. Then `app-data-gathering` part starts. First, in `workload identification` section steps are taken to make workload identification possible later on in the process. To be specific, all those operations are responsible for passing `app` label to do entry in one way or another. Then, in the `aggregate by pod` section, data from one pod is aggregated. Algorithm works in the scope of pod, however cadvisor reports in the scope of container, therefor aggregation is required. Then in `apps` section actual processing starts. First the number of memory access operations is counted, then, considering the mock pmem node characteristics, memory bandwidth is approximated. Then in the part `app-requirements` application memory and cpu requirements are assessed based on kube state metrics output. Again, workload is identified by `app` label. In the next section, `profiling`, first object describing app requirements is created, then it compares actual app needs with mock pmem node. In the end it returns a value, which meaning is described in algorithm section.
