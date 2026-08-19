1. **Your power diagnosis is plausible, but not established.**  
   With only 11 question-level pairs, the clustered test is intrinsically coarse and low-power. Eight wins out of 11 is directionally encouraging, but it is also compatible with substantial heterogeneity or luck.

   In fact, a two-sided sign test for 8/11 is about \(p=0.11\), very close to your reported \(p=0.10\). That means the result is mostly being driven by the count of question-level wins, not obviously by a few very large, consistently ranked improvements.

   Before spending money, inspect the per-question paired MAE differences:

   - Are the 8 improvements similar in magnitude, with 3 modest losses? That supports a broad, modest effect plus low power.
   - Are 2–3 questions responsible for nearly all aggregate response-level gain, while the rest are near zero or mixed? That supports a concentrated / question-dependent effect.
   - Are the questions highly unequal in number of responses? Then response-level MAE may be disproportionately reflecting the large clusters, whereas the clustered analysis deliberately gives each question equal weight.

   Also, because these are the *first* 11 questions in dataset order, they are not a random sample of the 46-question target population. More question coverage is needed not merely for power but for external validity to the intended “across questions” claim.

   So: **do not describe the current failure as “only a power problem.”** The accurate statement is: “The question-level result is suggestive but inconclusive; low \(n\) and possible question heterogeneity are both live explanations.”

2. **A rough target is about 35–45 total questions, with ~40 a reasonable planning number.**  
   Using the observed 8/11 direction rate as a simple sign-test proxy:

   - observed per-question win probability: \(8/11 \approx 0.73\);
   - for a two-sided \(\alpha=0.05\) test and roughly 80% power if the true win probability really is ~0.73, you need on the order of **40 independent questions**;
   - 46 questions should be in the rough **80–85% power** neighborhood under that optimistic “the current pattern persists” assumption.

   Since you already have 11, that means roughly **29 additional distinct questions** to reach 40, or preferably cover all remaining 35 and reach the dataset’s 46-question universe.

   Important caveat: that estimate is optimistic and conditional. With only 11 questions, the uncertainty around the true win probability is enormous. A true rate of 0.60 rather than 0.73 would require far more than 46 questions for reliable detection. And Wilcoxon power cannot be determined from win count alone: it depends on the distribution and rank ordering of the per-question MAE differences.

   The practical planning rule should be:

   - prioritize **more questions first**;
   - retain enough responses per question that each question’s mean error is not dominated by noise;
   - use approximately equal numbers of responses per question if feasible, or at least prespecify the sampling rule;
   - run the exact same frozen GPT pipeline and calibration procedure.

   If budget permits only, say, 5–10 new questions, I would **not** expect that to settle the clustered claim. It may be useful descriptively, but it is not a high-value confirmation attempt.

3. **For DeepSeek, I would not do open-ended backbone-specific prompt tuning on the remaining budget.**  
   You have already found one real failure mode—uncritical evidence trust—and fixed it. The resulting result is parity, not a win. Given the project history and the preregistered bar, repeatedly adjusting wording until DeepSeek crosses a threshold would have a very high risk of becoming post-hoc optimization.

   The one cheap diagnostic I would consider is a narrowly specified **evidence ablation**, not another wording search:

   > Keep the entire ConceptGrade verifier/scoring setup fixed, but omit the KG evidence block entirely.

   This answers a useful causal question: for DeepSeek, is KG evidence now merely neutral after skepticism prompting, or is it still slightly harmful / helpful relative to the rest of the ConceptGrade procedure?

   But I would treat it as a **diagnostic**, not a new claimed method, unless it is evaluated on genuinely unused questions with a prespecified comparison. If your existing zero-shot baseline already effectively answers that ablation, then do not spend on it.

   A more substantive future lever would be **evidence gating**: include KG evidence only when it passes a predeclared relevance/quality criterion, otherwise omit it. That is more defensible than prompt-wording iteration because it targets the identified failure mechanism: unreliable evidence is harmful when supplied indiscriminately. But it is not a $3 experiment if it requires developing and validating the gate. I would not start it now.

   Plainly: **with the stated budget, I would accept “DeepSeek parity under the tested protocol” as the honest current result and stop tuning it.**

4. **My priority order would be:**

   1. **No-cost analysis of the current GPT per-question effects.**  
      Make the per-question difference plot/table; report question sample sizes; inspect concentration; compute a leave-one-question-out sensitivity analysis; and simulate power using the observed question-level paired differences. This tells you whether the broader run is worth the money and documents uncertainty honestly.

   2. **If the budget can support meaningful coverage, spend it on a frozen, question-balanced GPT confirmation over remaining questions.**  
      Ideally evaluate all 46 questions, with a prespecified fixed number of student responses per question and a fixed seed/sampling rule. This directly addresses both the power and representativeness problem.

   3. **Do not spend the small budget trying to rescue DeepSeek via more prompt wording.**  
      At most, run the one prespecified evidence-ablation diagnostic if it is genuinely cheap and uses held-out questions. Otherwise stop.

   4. **Do not reinterpret the response-level \(p=5.8\times10^{-7}\) as resolving the clustered test.**  
      They answer different questions. The response-level result supports improvement over sampled responses; the clustered result is the relevant one for claiming robust improvement across question types.

My blunt recommendation: **put remaining spend toward GPT question coverage only if you can get close to 40 total questions, preferably all 46. If $3 cannot get you there with enough responses per question, do not run a token “broader” experiment that will still be underpowered. Analyze the existing per-question structure, report the GPT result as promising but preregistered-inconclusive, and report DeepSeek as parity.**