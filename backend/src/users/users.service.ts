import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { User, UserDocument } from './schemas/user.schema';

@Injectable()
export class UsersService {
  constructor(
    @InjectModel(User.name) private readonly userModel: Model<UserDocument>,
  ) {}

  /**
   * Find a user by their MongoDB _id.
   * Password hash is omitted by default (select: false).
   */
  async findById(id: string): Promise<UserDocument | null> {
    return this.userModel.findById(id).exec();
  }

  /**
   * Find a user by their email address (case-insensitive).
   * Password hash is omitted by default unless includePassword is true.
   */
  async findByEmail(
    email: string,
    includePassword = false,
  ): Promise<UserDocument | null> {
    const query = this.userModel.findOne({ email: email.toLowerCase() });
    if (includePassword) {
      query.select('+password');
    }
    return query.exec();
  }

  /**
   * Create a new user.
   */
  async create(userData: Partial<User>): Promise<UserDocument> {
    const createdUser = new this.userModel({
      ...userData,
      email: userData.email?.toLowerCase(),
    });
    return createdUser.save();
  }

  /**
   * Safely update profile fields (name, avatar) for an authenticated user.
   * Modifies only allowed properties, ignoring and preventing any updates
   * to email, password, authProvider, or system metadata.
   */
  async updateProfile(
    userId: string,
    updateData: { name?: string; avatar?: string },
  ): Promise<UserDocument | null> {
    const user = await this.userModel.findById(userId).exec();
    if (!user) {
      return null;
    }

    if (updateData.name !== undefined && typeof updateData.name === 'string') {
      user.name = updateData.name.trim();
    }
    if (updateData.avatar !== undefined && typeof updateData.avatar === 'string') {
      user.avatar = updateData.avatar;
    }

    return user.save();
  }

  /**
   * Read-only helper to count documents in the users collection.
   */
  async countUsers(): Promise<number> {
    return this.userModel.countDocuments().exec();
  }

  /**
   * Read-only helper to verify querying without exposing sensitive fields.
   */
  async findOneSanitized(): Promise<{ id: string; email: string; name: string } | null> {
    const user = await this.userModel.findOne().select('name email').exec();
    if (!user) return null;
    return {
      id: user._id.toString(),
      email: user.email,
      name: user.name,
    };
  }
}
