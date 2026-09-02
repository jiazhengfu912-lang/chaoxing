# :computer: 超星学习通自动化任务工具（改进版）

<p align="center">
    <a href="https://github.com/jiazhengfu912-lang/chaoxing" target="_blank" style="margin-right: 20px; font-style: normal; text-decoration: none;">
        <img src="https://img.shields.io/github/stars/jiazhengfu912-lang/chaoxing" alt="Github Stars" />
    </a>
    <a href="https://github.com/jiazhengfu912-lang/chaoxing" target="_blank" style="margin-right: 20px; font-style: normal; text-decoration: none;">
        <img src="https://img.shields.io/github/forks/jiazhengfu912-lang/chaoxing" alt="Github Forks" />
    </a>
    <a href="https://github.com/jiazhengfu912-lang/chaoxing" target="_blank" style="margin-right: 20px; font-style: normal; text-decoration: none;">
        <img src="https://img.shields.io/github/languages/code-size/jiazhengfu912-lang/chaoxing" alt="Code-size" />
    </a>
    <a href="LICENSE" target="_blank" style="margin-right: 20px; font-style: normal; text-decoration: none;">
        <img src="https://img.shields.io/github/license/jiazhengfu912-lang/chaoxing" alt="License" />
    </a>
</p>

> [!IMPORTANT]
> 本仓库基于 Samueli924 的 [chaoxing](https://github.com/Samueli924/chaoxing) 项目进行改进，基础版本为上游 `main` 分支提交 [`20d7070`](https://github.com/Samueli924/chaoxing/commit/20d7070c927dec40c50f809083b26d76052e7f50)。本仓库是独立维护的改进版，不代表上游项目的官方版本。

## :books: 项目作用

这是一个使用 Python 编写的超星学习通命令行自动化工具。程序登录后读取课程和章节任务卡，并通过现有处理流程完成视频、音频、直播、文档、阅读和作业等任务点；同时保留题库、通知、未开放章节处理和章节学习次数等上游功能。

## :sparkles: 本改进版新增内容

1. **单任务或多任务自由选择**：无参数启动并登录成功后，可选择一次只处理一个章节，或按指定并发数同时处理多个章节。
2. **原速或倍速自由选择**：可使用原速，也可设置 `1.0–2.0` 倍速；选择的速度会传递给视频、音频和直播处理。
3. **完成章节再次复核任务卡**：不再仅依据目录页的“已完成”状态跳过章节，避免 PPT 已完成但同章节视频尚未观看时发生漏刷。
4. **显示视频观看状态**：复核时明确输出“视频已观看”或“视频未观看，将开始观看”。
5. **修复无 `job` 字段视频被跳过**：未完成视频即使没有 `job` 字段，也会继续进入视频任务处理流程。
6. **增加无网络回归测试**：覆盖运行模式、并发数量、速度传递、混合 PPT/视频章节和无 `job` 字段视频等场景。

## :point_up: 上游更新记录
20241021更新通知： 感谢[sz134055](https://github.com/sz134055)提交代码[PR #360](https://github.com/Samueli924/chaoxing/pull/360)，**添加了对题库答题的支持**  

## :books: 使用方法

### 源码运行（Python 3.13+）

1. clone 项目至本地

```bash
git clone --depth=1 https://github.com/jiazhengfu912-lang/chaoxing.git
cd chaoxing
```

2. 安装依赖

```bash
pip install -r requirements.txt
```
或使用 `pip install .`（通过 pyproject.toml 安装依赖）

3. (可选直接运行)

```bash
python main.py
```

#### 无参数启动的交互选择

无参数运行时，登录成功后会依次询问任务执行方式和播放速度：

- 单任务：一次只处理一个章节。
- 多任务：输入同时处理的章节数，直接回车默认使用 4 个章节。
- 倍速播放：选择启用后输入 1.0 到 2.0 之间的播放速度；不启用时使用原速 1.0。

使用配置文件或命令行参数时不会弹出这些选择，可用于无人值守运行：`jobs = 1` 为单任务，`jobs >= 2` 为多任务；`speed = 1` 为原速，`speed > 1` 为倍速。

4. (可选配置文件运行)

> 复制config_template.ini文件为config.ini文件，修改文件内的账号密码内容

```bash
python main.py -c config.ini
```

5. (可选命令行运行)

```bash
python main.py -u 手机号 -p 密码 -l 课程ID1,课程ID2,课程ID3...(可选) -j 1 -s 1.5 -a [retry|ask|continue](可选)
```

其中 `-j 1` 表示单任务，`-j 2` 及以上表示多任务；`-s 1` 为原速，`-s <1.0-2.0>` 可设置播放倍速。

> Tips:  
> 如果已安装低版本 Python 推荐使用 `uv` 运行：

```bash
uv run --python 3.13 main.py
```

使用配置文件运行 ：
```bash
uv run --python 3.13 main.py -c config.ini
```

### 打包文件运行
本改进版暂不发布可执行文件。如需使用上游原版打包文件，可从[上游项目 Releases](https://github.com/Samueli924/chaoxing/releases)下载；上游打包文件不包含本仓库新增改进。

1. 从上游项目 Releases 下载 exe 文件
2. (可选直接运行) 双击运行即可
3. (可选配置文件运行) 下载config_template.ini文件保存为config.ini文件，修改文件内的账号密码内容, 执行 `./chaoxing.exe -c config.ini`
4. (可选命令行运行)`./chaoxing.exe -u "手机号" -p "密码" -l 课程ID1,课程ID2,课程ID3...(可选) -a [retry|ask|continue](可选)`

### Docker运行
1. 构建Docker镜像
   ```bash
   docker build -t chaoxing .
   ```

2. 运行Docker容器
   ```bash
   # 直接运行（将使用默认配置模板）
   docker run -it chaoxing
   
   # 使用自定义配置文件运行
   docker run -it -v /本地路径/config.ini:/config/config.ini chaoxing
   ```

3. 配置说明
   - Docker版本默认使用挂载到 `/config/config.ini` 的配置文件
   - 首次运行时，会自动将 `config_template.ini` 复制到该位置作为模板
   - 可以将本地编辑好的配置文件挂载到容器中，按照上述示例命令操作

### 题库配置说明

在你的配置文件中找到`[tiku]`，按照注释填写想要使用的题库名（即`provider`，大小写要一致），并填写必要信息，如token，然后在启动时添加`-c [你的配置文件路径]`即可。

题库会默认使用根目录下的`config.ini`文件中的配置，所以你可以复制配置模板（参照前面的说明）命名为`config.ini`，并只配置题库项`[tiku]`，这样即使你不填写账号之类的信息，不使用`-c`参数指定配置文件，题库也会根据这个配置文件自动配置并启用。

对于那些有章节检测且任务点需要解锁的课程，必须配置题库。

**提交模式与答题**
不配置题库（既不提供配置文件，也没有放置默认配置文件`config.ini`或填写要使用的题库）视为不使用题库，对于章节检测等需要答题的任务会自动跳过。
题库覆盖率：搜到的题目占总题目的比例
提交模式`submit`值为

- `true`：会答完题，达到题库题目覆盖率提交，没达到只保存，**正确率不做保证**。
- `false`：会答题，但是不会提交，仅保存搜到答案的，随后你可以自行前往学习通查看、修改、提交。**任何填写不正确的`submit`值会被视为`false`**

> 题库名即`answer.py`模块中根据`Tiku`类实现的具体题库类，例如`TikuYanxi`（言溪题库），在填写时，请务必保持大小写一致。

### 已关闭任务点处理配置说明

在配置文件的 `[common]` 部分，可以通过 `notopen_action` 选项配置遇到已关闭任务点时的处理方式:

- `retry` (默认): 遇到关闭的任务点时尝试重新完成上一个任务点，如果连续重试 3 次仍然失败 (或未配置题库及自动提交) 则停止
- `ask`: 遇到关闭的任务点时询问用户是否继续。选择继续后会自动跳过连续的关闭任务点，直到遇到开放的任务点
- `continue`: 自动跳过所有关闭的任务点，继续检查和完成后续任务点

也可以通过命令行参数 `-a` 或 `--notopen-action` 指定处理方式，例如：

```bash
python main.py -a ask  # 使用询问模式
```

### 章节学习次数配置说明

在配置文件的 `[common]` 部分，可以通过下面两个选项控制章节学习次数功能：

- `add_learning_count = false`：是否在完成刷课任务后，继续对课程章节执行学习次数增加
- `target_count = 100`：章节学习次数的目标总次数，程序会轮询课程章节直到达到该次数

当前实现会先完成所选课程的任务点，再统一执行章节学习次数增加流程。如果开启了 `add_learning_count`，它会作为刷课完成后的追加步骤执行，而不是独立模式。

**外部通知配置说明**

这功能会在所有课程学习任务结束后，或是程序出现错误时，使用外部通知服务推送消息告知你（~~有用但不多~~）

与题库配置类似，不填写视为不使用，按照注释填写想要使用的外部通知服务（也是`provider`，大小写要一致），并填写必要的`url`

## :test_tube: 测试

测试不需要连接超星平台：

```powershell
python -m unittest discover -s tests -v
```

当前测试覆盖单/多任务调度、播放速度传递、交互输入校验，以及混合 PPT/视频章节的复核与漏刷回归场景。真实平台登录和学习效果仍需使用者以自己的账号在本机验收。

## :heart: 上游项目与贡献者

本项目保留上游完整 Git 历史。以下统计和贡献者列表来自原项目 [Samueli924/chaoxing](https://github.com/Samueli924/chaoxing)，感谢原作者及所有上游贡献者。

![Alt](https://repobeats.axiom.co/api/embed/d3931e84b4b2f17cbe60cafedb38114bdf9931cb.svg "Repobeats analytics image")  

<a style="margin-top: 15px" href="https://github.com/Samueli924/chaoxing/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Samueli924/chaoxing" />
</a>

## :warning: 免责声明
- 本仓库基于采用 GPL-3.0 的上游源码，并继续按 [GPL-3.0 License](LICENSE) 发布。分发本项目或衍生版本时，请遵守许可证并保留相应的许可证与源码义务。
- 本代码仅用于学习、研究和技术交流。使用者应遵守所在地区法律法规、平台服务条款和学校相关规定。
- 他人或组织使用本代码进行的任何**违法行为**与本人无关
