#!/bin/bash
function get_parameters {
  FILES=/etc/config/*
  specjbb_paremeters=""
  for key in $FILES
  do
    specjbb_paremeters="${specjbb_paremeters} ${key}=$(cat $key)"
  done

  echo "$specjbb_paremeters"
  return "$specjbb_paremeters"
}
