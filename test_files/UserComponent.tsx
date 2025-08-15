import React from 'react';

interface UserProps {
  name: string;
  email: string;
}

export const UserComponent: React.FC<UserProps> = ({ name, email }) => {
  return (
    <div className="user-component">
      <h2>{name}</h2>
      <p>{email}</p>
    </div>
  );
};