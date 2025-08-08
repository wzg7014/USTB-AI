import React from "react";
import BotResponse from "./BotResponse";

const IntroSection = () => {
  return (
    <div id="introsection">
      <h1>
        USTB教务助手
        <BotResponse response=" - 您的智能教务问答专家" />
      </h1>
      <h2>
        基于先进AI技术的北京科技大学教务智能助手，为您提供准确、及时的教务信息查询和问答服务。
        无论是选课、成绩、学分还是各类教务政策，USTB教务助手都能为您提供专业解答。
      </h2>
      核心功能：
      <ul>
        <li>📚 教务政策智能问答</li>
        <li>📝 选课指导与建议</li>
        <li>📊 成绩查询与学分计算</li>
        <li>📋 考试安排与注意事项</li>
        <li>🔗 相关附件与链接推荐</li>
        <li>📱 移动端友好界面</li>
        <li>⚡ 7×24小时在线服务</li>
      </ul>
      <p>
        告别繁琐的教务信息查找，让USTB教务助手成为您的学习伙伴。
        基于最新的教务数据和政策文件，为您提供最准确的信息服务。
      </p>
    </div>
  );
};

export default IntroSection;
