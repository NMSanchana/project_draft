import {
  Controller,
  Put,
  Body,
  UseGuards,
  HttpCode,
  HttpStatus,
  NotFoundException,
} from '@nestjs/common';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { AuthenticatedUser } from '../auth/strategies/jwt.strategy';
import { UsersService } from './users.service';
import { UpdateProfileDto } from './dto/update-profile.dto';

@Controller('api/auth')
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  /**
   * Secure profile update endpoint.
   * Requires valid JWT Bearer authentication.
   * Derives user ID strictly from the verified JWT payload.
   * Any client-supplied 'id' or 'email' fields in the request body are ignored.
   */
  @UseGuards(JwtAuthGuard)
  @Put('profile')
  @HttpCode(HttpStatus.OK)
  async updateProfile(
    @CurrentUser() user: AuthenticatedUser,
    @Body() updateProfileDto: UpdateProfileDto,
  ) {
    const updated = await this.usersService.updateProfile(user.id, {
      name: updateProfileDto.name,
      avatar: updateProfileDto.avatar,
    });

    if (!updated) {
      throw new NotFoundException({
        success: false,
        message: 'User not found in database.',
      });
    }

    return {
      success: true,
      message: 'Profile updated in MongoDB Atlas successfully!',
      user: {
        id: updated._id.toString(),
        name: updated.name,
        email: updated.email,
        avatar: updated.avatar || '',
      },
    };
  }
}
