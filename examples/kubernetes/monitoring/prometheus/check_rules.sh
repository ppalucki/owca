#!/bin/zsh
#
if  ! type zsh >/dev/null; then
    echo "ERROR zsh (zsh for yaml) is required!"
    exit 1
fi

if  ! type promtool >/dev/null; then
    echo "ERROR promtool is required!"
    exit 1
fi

if  ! type yq >/dev/null; then
    echo "ERROR yq (jq for yaml) is required!"
    exit 1
fi

for f in prometheusrules*.yaml **/prometheusrules*.yaml; 
do 
    echo $f
    promtool check rules <(cat $f | yq .spec)
    
    if [ $? != 0 ]; then
        echo ERROR when checking above rules $f
        exit 1
    fi
done
