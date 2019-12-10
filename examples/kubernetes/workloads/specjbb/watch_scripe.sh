while true; do kubectl -n ddarczuk logs specjbb-0 -c controler -f; sleep 2; done
while true; do kubectl -n ddarczuk logs specjbb-0 -c backend -f; sleep 2; done
while true; do kubectl -n ddarczuk logs specjbb-0 -c injector -f; sleep 2; done
