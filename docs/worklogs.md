我用Claude Code写了一个程序，项目地址在~/projects/browsecomp-V3/，帮我对这个项目进行代码评审
我的环境是win10 + WSL，刚安装好antigravity，怎么才能让antigravity正常访问WSL

 ~/browsecomp-V2/目录下有一个项目，examples\generated_questions_demo.md，已经生成了10个Browsecomp风格的复杂问题，你再读读docs\COMPLEXITY_ANALYSIS.md这个文档，怎么才能生成Browsecomp风格的复杂问题

 我的github代码仓库地址：https://github.com/lzyq-hntvu/browsecomp-V3，用户凭证在 ~/projects/rag-course-gen/，我想让你写一个上传代码仓库的脚本

 昨天我玩了google的antigravity，模型总是报错，我的环境是win10 + WSL，我现在质疑这个环境的合理性，Claude Code是CLI，win10 + WSL的组合非常合理，WSL环境开发调试程序，win10 + VSCode可视化IDE。现在antigravity试图打通两个隔离的世界：win10 和 WSL。我感觉，MacOS下的antigravity才是正确的选择，都是Unix一脉，是不是搞开发的都用苹果的操作系统啊
 请阅读 /home/huyuming/projects/browsecomp-V3/docs/PROJECT_MEMORY.md
  了解项目当前状态，然后帮我
  为什么Phase 3: 约束扩展，你每次只实现一个约束
  10 种约束类型指的是什么？每一种约束是否对应constraint_to_graph_mapping.json中的一条规则（一共30条），为什么你只实现了10 种约束？

  项目输入端两个核心文件：推理链模板.md constraint_to_graph_mapping.json，一个是推理链模版，一个是30条规则，来源于另外一个项目中docs/reference/Browsecomp论文数据.md，这个项目在 ~/browsecomp-V2，我有一个疑问需要你验证：
  Browsecomp论文数据.md中的问题来源于互联网，是非常复杂的学术问题，而我们这个项目做的工作，是带着镣铐跳舞，7个推理链模板和30个规则在QandA项目中的知识图谱上都能应用吗

  我上午写了一个上传代码仓库的脚本，而且测试过可以用，而你吭哧吭哧写了半天，不仅不行，我能用的脚本你也说不行，请你检查原因，然后想办法解决
  请先阅读PROJECT_CONTEXT_MEMORY.md
  请你先阅读docs/CONSTRAINT_APPLICABILITY_ANALYSIS.md
  请你研究/home/huyuming/browsecomp-V2/examples/generated_questions_demo.md，这10个问题是怎么生成的？漏斗模型：先用规则过滤（筛选），再生成问题。藏宝图：先埋宝藏（定答案），再画地图（写问题）。
  请先阅读docs/PROJECT_MEMORY.md
  我想试试杨逸飞的思路，这样项目是不是要新建一个分支，我对这一块不懂
  直接在 /home/huyuming/projects/browsecomp-V3 下改代码，就是在 feature/dynamic-constraint-chain 分支上开发。
  为了正确理解杨逸飞的意图，我想让你先写一个spec，你觉得呢
  我感觉目前杨逸飞对于V3的思路不是很理解，现在是一个沟通的过程，如果坚持杨的思路，推理链模板.md和constraint_to_graph_mapping.json还能用吗？他一直说让胡云舒找规律