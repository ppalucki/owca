#!/bin/zsh
for f in prometheusrules*.yaml **/prometheusrules*.yaml; 
do 
    echo $f
    promtool check rules <(cat $f | yq .spec)
done
