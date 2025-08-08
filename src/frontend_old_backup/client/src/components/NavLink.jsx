import React from "react";

const NavLinks = ({ svg, link, text, setChatLog }) => {
  const handleClick = (text) => {
    if (text === "Clear Conversations") setChatLog([]);
    if (text === "Log out") {
      // 对于教务助手，我们不需要登出功能
      console.log("教务助手无需登出");
    }
  };

  return (
    <a
      href={link || "#"}
      target={link ? "_blank" : "_self"}
      rel="noreferrer"
      style={{ textDecoration: "none" }}
      onClick={(e) => {
        if (!link) e.preventDefault();
        handleClick(text);
      }}
    >
      <div className="navPrompt">
        {svg}
        <p>{text}</p>
      </div>
    </a>
  );
};

export default NavLinks;
