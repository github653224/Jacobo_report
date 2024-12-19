这个代码是启动 jacoco 代码行统计程序
java -javaagent:$JACOCO_HOME//lib/jacocoagent.jar=output=tcpserver -jar $TARGET_HOME/target/ruoyi-admin.jar

这个是收集最新代码行覆盖率命令
java -jar $JACOCO_HOME/lib/jacococli.jar dump --address 127.0.0.1 --port 6300 --destfile testcase.exec


这个是生成最新报告的命令
java -jar $JACOCO_HOME/lib/jacococli.jar report testcase.exec --html /Users/rock/Documents/test_projects/jacoco_report/templates --xml jacoco.xml --csv jacoco.csv --classfiles $TARGET_HOME/target/classes/ --sourcefiles $TARGET_HOME/src/main/java/



清空（之前的）并生成最新的覆盖率数据：
rm testcase.exec
java -jar $JACOCO_HOME/lib/jacococli.jar \
  dump \
  --address 127.0.0.1 --port 6300 \
  --reset \
  --destfile testcase.exec

不清空（之前的）并生成最新的覆盖率数据：
java -jar $JACOCO_HOME/lib/jacococli.jar \
  dump \
  --address 127.0.0.1 --port 6300 \
  --destfile testcase.exec


report：生成覆盖率报告
生成覆盖率报告并关联源码：

ava -jar $JACOCO_HOME/lib/jacococli.jar  \
  report testcase.exec \
  --html jacoco_report \
  --xml jacoco.xml \
  --csv jacoco.csv \
  --classfiles $TARGET_HOME/target/classes/ \
  --sourcefiles $TARGET_HOME/src/main/java/