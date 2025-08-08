import React, { useEffect } from "react";
import { useState } from "react";

const BotResponse = ({ response, chatLogRef }) => {
  const [botResoponse, setBotResponse] = useState("");
  const [isPrinting, setIsPrinting] = useState(true);
  const [isButtonVisible, setIsButtonVisible] = useState(false);

  useEffect(() => {
    let index = 1;
    let msg = setInterval(() => {
      if (response !== " - 您的智能教务问答专家") {
        setIsButtonVisible(true);
      }
      if (!isPrinting) {
        // if isPrinting is false, clear interval and return
        clearInterval(msg);
        return;
      }
      setBotResponse(response.slice(0, index));
      if (index >= response.length) {
        clearInterval(msg);
        setIsButtonVisible(false);
      }
      index++;

      // scroll to the bottom of the page whenever the messages array is updated
      if (chatLogRef !== undefined) {
        chatLogRef.current.scrollIntoView({
          behavior: "smooth",
          block: "end",
        });
      }
    }, 50);
    return () => clearInterval(msg); // clear interval on component unmount
  }, [chatLogRef, response, isPrinting]);

  const stopPrinting = () => setIsPrinting(!isPrinting);

  // 简单的Markdown渲染函数
  const renderMarkdown = (text) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // 粗体
      .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>') // 链接
      .replace(/\n/g, '<br/>'); // 换行
  };

  return (
    <>
      <div
        className="bot-response-content"
        dangerouslySetInnerHTML={{
          __html: renderMarkdown(botResoponse) + (botResoponse === response ? "" : "|")
        }}
      />
      {isButtonVisible && (
        <button className="stop-messgage" onClick={stopPrinting}>
          {isPrinting ? "停止输出" : "重新生成"}
        </button>
      )}
    </>
  );
};

export default BotResponse;
