import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';

export type UserDocument = HydratedDocument<User>;

@Schema({
  timestamps: true,
  collection: 'users',
})
export class User {
  @Prop({
    type: String,
    required: [true, 'Name is required'],
    trim: true,
  })
  name!: string;

  @Prop({
    type: String,
    required: [true, 'Email is required'],
    unique: true,
    lowercase: true,
    trim: true,
  })
  email!: string;

  @Prop({
    type: String,
    required: function (this: User) {
      return this.authProvider === 'local';
    },
    minlength: [6, 'Password must be at least 6 characters long'],
    select: false,
  })
  password?: string;

  @Prop({
    type: String,
    default: '',
  })
  avatar!: string;

  @Prop({
    type: String,
    enum: ['local', 'google'],
    default: 'local',
  })
  authProvider!: 'local' | 'google';

  createdAt?: Date;
  updatedAt?: Date;
}

export const UserSchema = SchemaFactory.createForClass(User);
